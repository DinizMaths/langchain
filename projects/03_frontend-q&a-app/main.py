import os

import streamlit as st

from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma


def load_document(file):
    import os
    name, extension = os.path.splitext(file)

    if extension == '.pdf':
        from langchain_community.document_loaders import PyPDFLoader

        print(f'Loading {file}')

        loader = PyPDFLoader(file)
    elif extension == '.docx':
        from langchain_community.document_loaders import Docx2txtLoader

        print(f'Loading {file}')

        loader = Docx2txtLoader(file)
    elif extension == '.txt':
        from langchain_community.document_loaders import TextLoader

        loader = TextLoader(file)
    else:
        print('Document format is not supported!')

        return None

    data = loader.load()

    return data

def chunk_data(data, chunk_size=256, chunk_overlap=20):
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(data)

    return chunks

def create_embeddings(chunks):
    embeddings = OpenAIEmbeddings()
    vector_store = Chroma.from_documents(chunks, embeddings)

    return vector_store

def ask_and_get_answer(vector_store, q, k=3):
    from langchain.chains import RetrievalQA
    from langchain_community.chat_models import ChatOpenAI

    llm = ChatOpenAI(
        model = 'gpt-3.5-turbo',
        api_key = os.environ.get('OPENAI_API_KEY'),
        temperature = 0
    )

    retriever = vector_store.as_retriever(
        search_type = 'similarity',
        search_kwargs = {'k': k}
    )

    chain = RetrievalQA.from_chain_type(
        llm = llm,
        chain_type = 'stuff',
        retriever = retriever
    )

    answear = chain.run(q)

    return answear

def compute_embedding_cost(chunks):
    import tiktoken

    enc = tiktoken.encoding_for_model('text-embedding-ada-002')
    total_tokens = sum([len(enc.encode(page.page_content)) for page in chunks])

    return (total_tokens, total_tokens / 1000 * 0.002)

def clear_history():
    if 'history' in st.session_state:
        del st.session_state.history

if __name__ == '__main__':
    import os
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(find_dotenv(), override=True)

    st.title('Frontend Q&A App')
    st.subheader('Ask a question about the document')

    with st.sidebar:
        api_key = st.text_input('OpenAI API Key', type='password')

        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key

        uploaded_file = st.file_uploader('Upload a document', type=['pdf', 'docx', 'txt'], on_change=clear_history)
        chunk_size = st.number_input('Chunk size', min_value=100, max_value=2048, value=256, on_change=clear_history)
        k = st.number_input('Number of answers', min_value=1, max_value=10, value=3)
        add_data = st.button('Add Data', on_change=clear_history)

        if uploaded_file and add_data:
            with st.spinner('Reading the document...'):
                bytes_data = uploaded_file.read()
                file_name = os.path.join("./", uploaded_file.name)
                
                with open(file_name, 'wb') as f:
                    f.write(bytes_data)

                data = load_document(file_name)
                chunks = chunk_data(data, chunk_size=chunk_size)

                st.write(f'Number of chunks: {len(chunks)}')

                tokens, cost = compute_embedding_cost(chunks)

                st.write(f'Total tokens: {tokens}')
                st.write(f'Cost: $ {cost:.2f}')

                vector_store = create_embeddings(chunks)

                st.session_state.vector_store = vector_store

                st.success('Data added successfully!')

    q = st.text_input('Question:')

    answer = None

    if q:
        if 'vector_store' in st.session_state:
            vector_store = st.session_state.vector_store

            answer = ask_and_get_answer(vector_store, q, k=k)

            st.write("Answer:", answer)

            st.divider()

            if 'history' not in st.session_state:
                st.session_state.history = ''

            value = f"Q: {q}\nA: {answer}\n"

            if answer:
                st.session_state.history = f"{value} \n {'-'*100} \n {st.session_state.history}"

            h = st.session_state.history

            st.text_area('History', h, key='history', height=400)