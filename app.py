import streamlit as st
from model.local_qa import get_local_qa
from model.web_agent import get_web_agent
from model.memory import memory

st.set_page_config(page_title="Banking Assistant", layout="centered")
st.title("💬 Banking AI Assistant with Memory")
st.markdown("Ask general banking queries. It will use local docs first, then search the web.")

query = st.text_input("🔍 Your question:")

if query:
    with st.spinner("Searching local documents..."):
        qa_chain = get_local_qa()
        result = qa_chain({"question": query})

    if result["answer"] and "I don't know" not in result["answer"]:
        st.subheader("📄 Answer from Documents")
        st.write(result["answer"])

        with st.expander("📁 Source Files"):
            for doc in result["source_documents"]:
                st.markdown(f"**File**: `{doc.metadata.get('source')}`")
                st.markdown(doc.page_content[:400] + "...")
    else:
        st.warning("Nothing found locally. Searching web...")
        with st.spinner("🔍 Searching online..."):
            agent = get_web_agent()
            web_result = agent.run(query)
            st.subheader("🌐 Web Answer")
            st.write(web_result)

# Chat history view
with st.expander("🧠 Memory (Conversation History)"):
    for m in memory.chat_memory.messages:
        role = "User" if m.type == "human" else "AI"
        st.markdown(f"**{role}:** {m.content}")
