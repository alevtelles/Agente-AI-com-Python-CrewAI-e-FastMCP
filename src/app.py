import streamlit as st
import asyncio
from fastmcp import Client
import json
import pandas as pd
import uuid
import nest_asyncio

nest_asyncio.apply()

st.set_page_config(page_title="Analista de Múltiplos Agentes", page_icon="🤖", layout="wide")
st.title("Analista de Múltiplos Agentes – Interface de Chat com IA")

if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

async def call_agent(question: str, user_id: str):
    try:
        # Usar URL base sem endpoint específico
        client = Client("http://127.0.0.1:8000/mcp", timeout=30)

        async with client:
            result = await client.call_tool(
                "mult_analyst",
                {"question": question, "user_id": user_id},
                timeout=20  # Timeout para a chamada específica
            )
        return result[0].text if result and hasattr(result[0], "text") else str(result)
    except Exception as e:
        st.error(f"Erro na comunicação: {str(e)}")
        return f"Erro detalhado: {str(e)}"
    

if prompt := st.chat_input("Faça a sua pergunta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Aguarde..."):
            try:
                response = asyncio.run(call_agent(prompt, st.session_state.user_id))
                
                try:
                    resp_json = json.loads(response)

                    if isinstance(resp_json, dict):
                        if(
                            "tasks_output" in resp_json
                            and isinstance(resp_json["tasks_output"], list)
                            and len(resp_json["tasks_output"]) > 0
                            and "raw" in resp_json["tasks_output"][0]
                        ):
                            display_data = resp_json["tasks_output"][0]["raw"]
                        elif "raw" in resp_json:
                            display_data = resp_json["raw"]
                        else:
                            display_data = response


                except Exception:
                    display_data = response

                try:
                    data = json.loads(display_data)
                    if isinstance(data, list) and all(
                        isinstance(row, dict) for row in data
                    ): 
                        df = pd.DataFrame(data)
                        st.dataframe(df)
                        response = None
                    
                    else:
                        st.json(data)
                        response = None
                except Exception:
                    response = display_data
            
            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                response = f"Error: {e}\n\nTraceback:\n{tb}"
            if response:
                st.markdown(response)

    st.session_state.messages.append({
        "role": "assistante",
        "content": response if response else "[Structured output above0]",
    })