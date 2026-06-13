"""
Indexes a policy PDF into Azure AI Search (policy-docs index).
Pipeline: PDF -> Document Intelligence -> chunk by section -> embed -> AI Search

Usage:
    python indexing/index_policy.py
"""

import os, hashlib
from dotenv import load_dotenv
load_dotenv(override=True)

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# ── Clients ───────────────────────────────────────────────────────────

doc_client = DocumentIntelligenceClient(
    endpoint=os.getenv("AZURE_DOC_INTEL_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_DOC_INTEL_KEY"))
)

search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_POLICY_INDEX"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

# ── Section classifier ────────────────────────────────────────────────

SECTION_KEYWORDS = {
    "exclusion":          "exclusions",
    "does not apply":     "exclusions",
    "not covered":        "exclusions",
    "we will not pay":    "exclusions",
    "condition":          "conditions",
    "duty":               "conditions",
    "definition":         "definitions",
    "means ":             "definitions",
    "insuring agreement": "insuring_agreement",
    "we will pay":        "insuring_agreement",
    "we agree to pay":    "insuring_agreement",
    "declarations":       "declarations",
    "named insured":      "declarations",
    "policy period":      "declarations",
    "endorsement":        "endorsement",
    "amendment":          "endorsement",
}

def classify_section(text: str) -> str:
    t = text.lower()
    for keyword, section in SECTION_KEYWORDS.items():
        if keyword in t:
            return section
    return "body"

# ── Embedding ─────────────────────────────────────────────────────────

def get_embedding(text: str) -> list:
    response = openai_client.embeddings.create(
        input=text[:8000],  # ada-002 token limit safety
        model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
    )
    return response.data[0].embedding

# ── Main indexing function ────────────────────────────────────────────

def index_policy(pdf_path: str, policy_id: str, form_number: str = "CA-00-01"):
    print(f"\nIndexing: {pdf_path}")
    print(f"  Policy ID : {policy_id}")
    print(f"  Form      : {form_number}")

    # Step 1: Extract with Document Intelligence
    print("  Extracting text via Document Intelligence...")
    with open(pdf_path, "rb") as f:
        poller = doc_client.begin_analyze_document(
            "prebuilt-layout",
            body=f,
            content_type="application/octet-stream"
        )
    result = poller.result()
    print(f"  Extracted {len(result.paragraphs)} paragraphs from {len(result.pages)} pages")

    # Step 2: Chunk and classify
    chunks = []
    current_section = "body"

    for i, para in enumerate(result.paragraphs):
        text = para.content.strip()

        # Skip very short lines (headers, page numbers)
        if len(text) < 60:
            continue

        # Update running section
        detected = classify_section(text)
        if detected != "body":
            current_section = detected

        page = para.bounding_regions[0].page_number if para.bounding_regions else 0
        chunk_id = hashlib.md5(f"{policy_id}-{i}".encode()).hexdigest()

        chunks.append({
            "id":           chunk_id,
            "content":      text,
            "policy_id":    policy_id,
            "section_type": current_section,
            "form_number":  form_number,
            "page_number":  page,
        })

    print(f"  Created {len(chunks)} chunks")

    # Step 3: Embed and upload in batches
    print("  Embedding and uploading to AI Search...")
    batch_size = 10  # small batches to avoid rate limits on Free tier embedding
    uploaded = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        for chunk in batch:
            chunk["content_vector"] = get_embedding(chunk["content"])

        search_client.upload_documents(batch)
        uploaded += len(batch)
        print(f"  Uploaded {uploaded}/{len(chunks)} chunks...")

    print(f"  Done. {policy_id} indexed with {len(chunks)} chunks.")
    return len(chunks)


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(__file__), "..", "sample_data")

    policies = [
        ("policy_ca0001_2010.pdf",              "CA0001-2010",   "CA-00-01-03-10"),
        ("policy_ca0001_2013.pdf",              "CA0001-2013",   "CA-00-01-10-13"),
        ("Hiscox CG 00 01 2007.pdf",            "CG0001-2007",   "CG-00-01-12-07"),
        ("Sonoma County CG 00 01 2013.pdf",     "CG0001-2013",   "CG-00-01-04-13"),
        ("WCRB Workers Comp WC 00 00 00 C.pdf", "WC000000C",     "WC-00-00-00-C"),
        ("State Fund CA Workers Comp.pdf",      "WC-STATEFUND",  "CA-WC-STATEFUND"),
        ("WBASNY Commercial Umbrella.pdf",      "UMBRELLA-WBASNY","CU-UMBRELLA"),
    ]

    total = 0
    for filename, policy_id, form_number in policies:
        pdf_path = os.path.join(base, filename)
        if os.path.exists(pdf_path):
            total += index_policy(pdf_path=pdf_path, policy_id=policy_id, form_number=form_number)
        else:
            print(f"  SKIPPED (file not found): {filename}")

    print(f"\nAll done. Total chunks indexed: {total}")
