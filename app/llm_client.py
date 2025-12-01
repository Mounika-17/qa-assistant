import os
from typing import List, Dict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from .rag_store import get_retriever

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set. "
        "Set it in a .env file for local dev or as an environment variable for Docker/EC2."
    )

# This is the system prompt for the LLM and sets the role + behavior + scope of the QA assistant.
# .strip() removes extra leading/trailing whitespace.
QA_SYSTEM_PROMPT = """
You are a senior QA engineer and QA mentor.

You have access to a QA knowledge base that contains:
- Fundamentals of testing (ISTQB oriented)
- Test design techniques (BVA, EP, decision tables, etc.)
- Bug reporting and defect lifecycle
- API testing practices and tools
- Agile testing and QA role in Scrum
- Common QA interview questions and structured answers

Use the provided context from this knowledge base as the primary source of truth.
If the context is not sufficient, you may use your own general knowledge, but
clearly state any assumptions.

Always:
- Use simple, practical language.
- Connect theory with real-world examples.
- For test cases, include steps, data, and expected results.
- For bug reports, include title, steps, expected vs actual, severity, and priority.
""".strip()

chat_model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GEMINI_API_KEY,
    temperature=0.3, # 0.3 is lower means more deterministic and less random
)

# we fill the context with the RAG-retrieved text
# {history} is a placeholder for the chat history, previous chat turns of the user and assistant
# {input} is a placeholder for the latest user input
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", QA_SYSTEM_PROMPT),
        ("system",
            "Use the following QA reference material to answer. "
            "If there is any conflict, prefer the reference material.\n\n"
            "Context:\n{context}",
        ),
        ("placeholder", "{history}"),
        ("human", "{input}"),
    ]
)

# Convert the frontend format (user/assistant) into LangChain format (human/ai) and separate current question from history.
def convert_history_for_langchain(messages: List[Dict[str, str]]):
    """
    Convert frontend messages:
      [{"role": "user"/"assistant", "content": "..."}, ...]
    into:
      history: [("human"/"ai", text), ...]
      latest_input: str
    """
    # if no messages return empty history and empty input
    if not messages:
        return [], ""
    # otherwise take the last message as latest input
    last_message = messages[-1]
    latest_input = last_message["content"]

    history_pairs = []
    # Take all the messages except the last message
    for m in messages[:-1]:
        if m["role"] == "user":
            history_pairs.append(("human", m["content"]))
        else:
            history_pairs.append(("ai", m["content"]))

    return history_pairs, latest_input


def build_context(query: str) -> str:
    """
    Use the retriever to fetch relevant QA knowledge base chunks
    and combine them into a single context string.
    """
    retriever = get_retriever()  # method from the rag_store.py file
    docs = retriever.invoke(query) # ask FAISS for the most similar chunks to the question.

    chunks = []
    for d in docs:
        chunks.append(d.page_content) #collect the .page content into chunks
    
    # Join the seperator to every chunk in the chunks for the readability
    context = "\n\n---\n\n".join(chunks)
    return context


def get_qa_response(messages: List[Dict[str, str]]) -> str:
    """
    Main entry for the app:
    - Uses RAG: retrieves relevant context from knowledge base (PDFs)
    - Feeds context + history + latest user input to Gemini via LangChain
    """
    # get the history and latest input from the messages
    history_pairs, latest_input = convert_history_for_langchain(messages)
    # Retrieve relevant chunks via FAISS based on the latest question.
    context = build_context(latest_input)
    # LCEL composition: prompt → model
    chain = prompt | chat_model
    
    response = chain.invoke(
        {
            "history": history_pairs,
            "input": latest_input,
            "context": context,
        }
    )
    
    return response.content
