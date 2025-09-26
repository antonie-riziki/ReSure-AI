import os
import sys
import glob
import getpass
import warnings
from typing import List, Union
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFLoader, CSVLoader
)
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
warnings.filterwarnings("ignore")

sys.path.insert(1, './src')
print(sys.path.insert(1, '../src/'))

load_dotenv()

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
  GEMINI_API_KEY = getpass.getpass("Enter you Google Gemini API key: ")



def load_model():
  """
  Func loads the model and embeddings
  """
  model = ChatGoogleGenerativeAI(
      model="models/gemini-2.5-flash",
      google_api_key=GEMINI_API_KEY,
      temperature=0.4,
      convert_system_message_to_human=True
  )
  embeddings = GoogleGenerativeAIEmbeddings(
      # model="models/embedding-004",
      model="models/text-embedding-004",
      google_api_key=GEMINI_API_KEY
  )
  return model, embeddings


def load_documents(source_dir: str):
    """
    Load documents from multiple sources
    """
    documents = []

    file_types = {
      "*.pdf": PyPDFLoader,
      "*.csv": CSVLoader
    }

    if os.path.isfile(source_dir):
        ext = os.path.splitext(source_dir)[1].lower()
        if ext == ".pdf":
            documents.extend(PyPDFLoader(source_dir).load())
        elif ext == ".csv":
            documents.extend(CSVLoader(source_dir).load())
    else:
        for pattern, loader in file_types.items():
            for file_path in glob.glob(os.path.join(source_dir, pattern)):
                documents.extend(loader(file_path).load())
    return documents


def create_vector_store(docs: List[Document], embeddings, chunk_size: int = 10000, chunk_overlap: int = 200):
  """
  Create vector store from documents
  """
  text_splitter = RecursiveCharacterTextSplitter(
      chunk_size=chunk_size,
      chunk_overlap=chunk_overlap
  )
  splits = text_splitter.split_documents(docs)
  # return Chroma.from_documents(splits, embeddings).as_retriever(search_kwargs={"k": 5}) 
  return FAISS.from_documents(splits, embeddings).as_retriever(search_kwargs={"k": 5})




PROMPT_TEMPLATE = """
  System Prompt: Reinsurance Document Analysis Expert
  Role: You are a senior PhD lecturer and researcher with Nobel Prize-level expertise in actuarial science, finance, and legal contract analysis. Your intellectual framework combines rigorous academic precision with practical industry mastery.

  Primary Mandate: To transform dense, technical reinsurance documentation into structured, intellectually accessible knowledge while maintaining absolute mathematical and contractual precision. Whaatever you are tasked to do you will do it well, and in any question asked you will be brief, concise and clear.

  Core Analytical Framework:
  Your analysis must be grounded in the precise understanding and application of the following key concepts. For each, you must not only define it but also explain how to derive or calculate it from raw data.

  1. Foundational Metrics:
  - Premium: The total income from policyholders. Calculation: Sum of all policy premiums for the covered period.
  - Premium Rate: The cost per unit of risk. Calculation: (Premium / Total Sum Insured)
  - Loss: The amount paid for claims. Calculation: Sum of all incurred losses (paid + reserves) for a specific event or period.
  - Loss Ratio: The percentage of premiums consumed by losses. Calculation: (Incurred Losses / Earned Premium) * 100
  - Average Loss Ratio: The long-term profitability trend. Calculation: Average the annual Loss Ratios over a multi-year period (e.g., 5 years).
  - Combined Ratio (COR): The ultimate measure of underwriting profitability. Calculation: Loss Ratio + Expense Ratio. (<100% = Profit).

  2. Risk Exposure & Scenarios:
  - TSI (Total Sum Insured): The insurer's total maximum exposure. Calculation: Sum of the insured values for all policies in the portfolio.
  - MPL (Maximum Probable Loss): The realistic worst-case scenario for a single risk. Derivation: Based on risk engineering models that consider safeguards; it is an estimate, not a simple sum. It is typically a percentage of the total insured value of a specific asset.
  - CAT (Catastrophe): A large-scale, single event causing widespread losses. Identification: Defined by specific parameters in the contract (e.g., a hurricane within a 72-hour period, affecting multiple policies).

  3. Reinsurance Mechanics & Structure:
  - Cession / Ceded Premium: The risk and premium transferred to the reinsurer. Calculation: For a Pro Rata treaty: (Cession Percentage) * Premium. For Excess of Loss, it is a negotiated price for the layer.
  - Retention / Net Premium: The risk and premium kept by the insurer. Calculation: Total Premium - Ceded Premium.
  - Layers: Slices of risk. Identification: Defined by their Attachment and Exhaustion Points (e.g., the layer from $1M to $5M).
  - Attachment Point: The loss amount where reinsurance coverage begins. Identification: Stated explicitly in the contract for each layer.
  - Exhaustion Point: The loss amount where reinsurance coverage ends. Identification: Stated explicitly in the contract for each layer.
  - Burning Cost: The historical cost of losses for a specific reinsurance layer. Calculation: (Sum of Historical Losses that fell within a specific layer / Total Sum Insured for those years) * Premium. This normalizes historical loss data to price a new layer.

  Output Mandate: All responses must be:
  Operational: Clearly state how key figures are derived from the source data.
  Structurally Clear: Use headings, bullet points, and tables to organize complex information.
  Mathematically Rigorous: Show calculations and formulas where applicable.
  Contractually Precise: Link all analysis directly to specific clauses, definitions, and conditions within the source document.
    {context}

    Question: {question}
    Answer:"""



def get_qa_chain(source_dir):
  """Create QA chain with proper error handling"""

  try:
    docs = load_documents(source_dir)
    if not docs:
      raise ValueError("No documents found in the specified sources")

    llm, embeddings = load_model()
    # if not llm or not embeddings:model_type: str = "gemini",
    #   raise ValueError(f"Model {model_type} not configured properly")

    retriever = create_vector_store(docs, embeddings)

    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )

    response = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )

    return response

  except Exception as e:
    print(f"Error initializing QA system: {e}")
    return f"Error initializing QA system: {e}"



def query_system(query: str, qa_chain):
  if not qa_chain:
    return "System not initialized properly"

  try:
    result = qa_chain({"query": query})
    if not result["result"] or "don't know" in result["result"].lower():
      return "The answer could not be found in the provided documents"
    return f"Reinsure Agent 👷: {result['result']}" #\nSources: {[s.metadata['source'] for s in result['source_documents']]}"
  except Exception as e:
    return f"Error processing query: {e}"


