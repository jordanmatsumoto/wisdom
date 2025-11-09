import base64
import glob
import os
from dotenv import load_dotenv
import gradio as gr
from chromadb import Client
from openai import OpenAI
import pandas as pd

# Set constants
MODEL = "gpt-4o-mini"
DB_NAME = "vector_db"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200

# Load environment variables
load_dotenv(override=True)
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'your-key-if-not-using-env')

# Initialize OpenAI client
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# Load documents
folders = glob.glob("mirai_nexus_data/*")
documents = []

for folder in folders:
    if not os.path.isdir(folder):
        continue
    doc_type = os.path.basename(folder)

    # Load Markdown files
    md_files = glob.glob(os.path.join(folder, "**/*.md"), recursive=True)
    for md_file in md_files:
        with open(md_file, "r", encoding="utf-8") as f:
            text = f.read()
        documents.append({
            "content": text,
            "metadata": {
                "doc_type": doc_type,
                "filename": os.path.basename(md_file),
                "filepath": md_file
            }
        })

    # Load CSV files
    csv_files = glob.glob(os.path.join(folder, "**/*.csv"), recursive=True)
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        documents.append({
            "content": df.to_csv(index=False),
            "metadata": {
                "doc_type": doc_type,
                "filename": os.path.basename(csv_file),
                "filepath": csv_file
            }
        })

# Split documents into chunks
def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

chunks = []
for doc in documents:
    for chunk in chunk_text(doc["content"]):
        chunks.append({"content": chunk, "metadata": doc["metadata"]})

# Create vector store
chroma_client = Client()
collection = chroma_client.get_or_create_collection(DB_NAME)

for i, chunk in enumerate(chunks):
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=chunk["content"]
    )
    embedding = resp.data[0].embedding
    collection.add(
        ids=[str(i)],
        embeddings=[embedding],
        metadatas=[chunk["metadata"]],
        documents=[chunk["content"]]
    )

# System prompt
SYSTEM_PROMPT = """
You are a helpful assistant. First use the following documents to answer the 
question. If the document is a CSV, parse it correctly and return data in a 
readable table or JSON format. Do not make up data. If the answer is not in the 
documents, offer suggestions based on what is in your knowledge base and 
continue being a helpful assistant that answers all questions raised by the user.
"""

# Chat function
conversation_history = []

def chat(user_message):
    """Get assistant response for a user message."""
    conversation_history.append(f"User: {user_message}")

    # Retrieve top chunks
    user_embedding = client.embeddings.create(
        model="text-embedding-3-small",
        input=user_message
    ).data[0].embedding

    results = collection.query(query_embeddings=[user_embedding], n_results=5)

    # Create links from metadata
    retrieved_metas = results["metadatas"][0]
    links = [
        f'<a href="file://{meta["filepath"]}" target="_blank">{meta["filename"]}</a>'
        for meta in retrieved_metas
    ]
    links_html = "<br>".join(links)

    # Combine the documents for context to feed to the model
    retrieved_docs = results["documents"][0]
    context = "\n\n".join(retrieved_docs)

    prompt = (
        f"{SYSTEM_PROMPT}\n"
        f"Documents:\n{context}\n"
        f"Conversation history:\n{chr(10).join(conversation_history)}\n"
        f"User question: {user_message}\n"
        "Answer:"
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = resp.choices[0].message.content
    conversation_history.append(f"Assistant: {answer}")

    return answer, links_html

# Gradio chat wrapper
def gradio_chat(user_message, history):
    """Handle chat for Gradio interface."""
    answer, sources = chat(user_message)
    history.append((user_message, answer))
    return history, "", sources

# Create the Gradio UI
with open("assets/icons/wisdom_icon.png", "rb") as f:
    icon_b64 = base64.b64encode(f.read()).decode()

# Theme with subtle background and block styling
theme = gr.themes.Base().set(
    body_background_fill="#f8fafc",
    block_border_width="2px",
    block_shadow="0 2px 12px rgba(0,0,0,0.08)",
)

with gr.Blocks(theme=theme, title="Wisdom") as ui:

    with gr.Row():
        gr.Markdown(
            f"""
            <div style="
                display:flex;
                flex-direction:column;
                align-items:center;
                justify-content:center;
            ">
                <div style="
                    background:#f8fafc;
                    padding:0.5em;
                    border-radius:12px;
                    display:flex;
                    justify-content:center;
                    align-items:center;
                ">
                    <img src="data:image/png;base64,{icon_b64}" width="150" height="150" style="display:block;"/>
                </div>
            </div>
            """,
            elem_id="title"
        )

    # Chatbot and input controls        
    with gr.Row(equal_height=True):
        chatbot = gr.Chatbot(label="Wisdom", height=500)
        doc_viewer = gr.HTML(
            value="<i style='color:gray;'>Related documents will appear here...</i>",
            label="Source Documents",
            elem_id="source-docs",
            interactive=False
        )

    with gr.Row():
        msg = gr.Textbox(placeholder="Ask Wisdom a question...", lines=1)
    with gr.Row():
        clear = gr.Button("Clear Conversation", variant="primary")

        # UI actions
        msg.submit(gradio_chat, [msg, chatbot], [chatbot, msg, doc_viewer])
        clear.click(lambda: ([], "", ""), None, [chatbot, msg, doc_viewer])

    # Footer
    gr.Markdown(
        """
        <p style='text-align:center; font-size:1em; color:#000000; margin-top:2em;'>
        © 2025 Wisdom — Built by Jordan Matsumoto with OpenAI & Gradio
        </p>
        """
    )

ui.launch(share=True, inbrowser=True)