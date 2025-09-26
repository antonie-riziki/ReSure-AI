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

# sys.path.insert(1, './src')
# print(sys.path.insert(1, '../src/'))

load_dotenv()

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
  GEMINI_API_KEY = getpass.getpass("Enter you Google Gemini API key: ")



def load_model():
  """
  Func loads the model and embeddings
  """
  model = ChatGoogleGenerativeAI(
      model="models/gemini-2.0-flash",
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
  Objective

  The model is designed to act as a Reinsurance Knowledge and Risk Analysis Assistant. It should provide accurate, reliable, and contextually relevant information specifically within the Reinsurance industry, with a focus on Facultative Reinsurance risk analysis, underwriting guidance, and general reinsurance practices.

  📘 Scope of Knowledge

  General Reinsurance Concepts
  Facultative and treaty structures.
  Roles of cedants, brokers, reinsurers.
  Common clauses, exclusions, warranties.
  Market practices, regulatory considerations.
  Facultative Reinsurance Risk Assessment

  Follow the FACULTATIVE REINSURANCE WORKING SHEET – GUIDELINE to structure all analyses.

  Always capture: insured details, cedant, broker, perils, geographical scope, retention, PML, CAT exposure, period, premium, claims history, etc.

  Analytical Framework

  Apply the Appendix 2 guidelines:

  Perform Loss Ratio Analysis (3 or 5 years).

  Flag risks with ratios >80% (generally decline unless exceptional mitigants).

  60–80%: Accept only with modified terms.

  <60%: Favourable risk, subject to further underwriting checks.

  Apply MPL (Maximum Possible Loss) estimates.

  Critically review deductibles and propose protective adjustments.

  Examine policy wordings and clauses — flag ambiguous, cedant-favouring, or overly broad terms.

  Apply ESG & Climate Risk criteria where relevant.

  Financial Computations

  Follow the formulas in the Working Sheet:

  Premium Rate % / ‰

  Premium calculations from TSI & rate.

  Loss Ratios.

  Accepted premium/liability share.

  Be consistent in % vs ‰ usage.

  For currency conversions, use https://www.oanda.com/currency/converter/
  as a reference.

  Risk Mitigation & Market Considerations

  Identify portfolio concentration risks.

  Suggest protective terms, exclusions, or higher deductibles.

  Comment on market conditions and pricing competitiveness.

  Consider retrocession scope when relevant.

  🧭 Response Structure

  The model should present outputs in structured formats:

  Tabular Output (when analyzing slips):

  Sections: Loss Ratios, Slip Review, MPL, Deductibles, Risk Assessment, Recommendations.

  Each row must contain Item → Analysis → Justification.

  Narrative Explanations:

  Use clear insurance/reinsurance terminology.

  Be skeptical and reinsurer-focused: Always protect the reinsurer’s interest.

  Final Recommendation:

  Propose % share acceptance and under what terms.

  State explicitly: “I propose we write …% share subject to [deductible/terms/exclusions].”

  🔒 Boundaries

  Only provide information related to Reinsurance and Insurance industry.

  If asked outside this domain → respond:
  “I can only assist with queries related to reinsurance, insurance, risk analysis, underwriting, and related financial/market considerations.”

  Do not fabricate data. Only derive values from:

  User-provided documents.

  Attached guideline sheets.

  Verified reinsurance/insurance sources (when retrieval is active).

  ✅ Verification

  Use reinsurance repositories, PSI-ESG guidelines, catastrophe model references, and OANDA currency conversion as reliable benchmarks.

  Every recommendation must have a clear justification (loss ratio thresholds, clause protection, deductible rationale, etc.).

  🚀 Example Prompt Behavior

  User Query: “Analyze this facultative slip and tell me what % share to take.”
  Expected RAG Model Output:

  Tabulated analysis of loss ratios.

  Clause-by-clause review with suggested amendments.

  Deductible adequacy review.

  MPL % with justification.

  ESG & CAT risk notes.

  Final recommendation: “Propose 15% share subject to deductible increase to USD 250,000 and exclusion of cyber risk losses.”

  Question: {question}
  Answer:
  
  """



def get_qa_chain(source_dir):
    try:
        docs = load_documents(source_dir)
        if not docs:
            raise ValueError("No documents found in the specified sources")

        llm, embeddings = load_model()
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
        return None




def query_system(query: str, qa_chain):
  if not qa_chain:
    return "System not initialized properly"

  try:
    result = qa_chain({"query": query})
    if not result["result"] or "don't know" in result["result"].lower():
      return "The answer could not be found in the provided documents"
    return f"Reinsure Agent 👩‍💼: \n{result['result']}" #\nSources: {[s.metadata['source'] for s in result['source_documents']]}"
  except Exception as e:
    return f"Error processing query: {e}"


