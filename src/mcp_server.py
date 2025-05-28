from dotenv import load_dotenv
from fastmcp import FastMCP
from langchain_openai import ChatOpenAI
from crewai import Agent, Task, Crew, Process
from crewai.memory import EntityMemory
from crewai.memory.storage.rag_storage import RAGStorage
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters 
import os

load_dotenv()
mcp = FastMCP("multi-agent-server")

# function for per-user memory
def get_user_memory(user_id: str):
    return EntityMemory(
        storage=RAGStorage(
            embedder_config={
                "provider": "openai",
                "config": {"model": "text-embedding-3-small"},
            },
            type="short_term",
            path=f"./memory_story/{user_id}",
        )
    )

@mcp.tool(name="mult_analyst")
async def multi_analyst_tool(question: str, user_id: str) -> str:
    """ Resolva questões financeiras e de BD usando acesso unificado a ferramentas."""
    yfinance_params = StdioServerParameters(command="uvx", args=["yfmcp@latest"])
    supabase_params = StdioServerParameters(
        command="npx",
        args=["-y", "@supabase/mcp-server-supabase@latest"],
        env={"SUPABASE_ACCESS_TOKEN": os.getenv("SUPABASE_ACCESS_TOKEN"), **os.environ}
    )
    mcp_adapter = []

    try: 
        yfanance_adapter = MCPServerAdapter(yfinance_params)
        supabase_adapter = MCPServerAdapter(supabase_params)
        mcp_adapters = [yfanance_adapter, supabase_adapter]

        tools = yfanance_adapter.tools + supabase_adapter.tools
        llm = ChatOpenAI(model="gpt-4.1-mini")
        memory = get_user_memory(user_id)

        multi_analyst = Agent(
            role="Analista profissional de dados e finanças",
            goal="Responda a qualquer pergunta financeira ou sobre banco de dados usando as ferramentas YFinance e Supabase.",
            backstory="Especialista em SQL, ações, KPIs e bancos de dados. Determina a melhor ferramenta para cada consulta.",
            tools=tools,
            verbose=True,
            llm=llm,
            allow_delegation=False,
            memory=memory, 
        )

        task = Task (
            description=f"Responder a esta pergunta do usuário: {question}",
            expected_output="Resposta útil usando a ferramenta mais adequada.",
            tools=tools,
            agent=multi_analyst,
            memory=memory,
        )

        crew = Crew (
            agents=[multi_analyst],
            tasks=[task],
            process=Process.sequential,
            memory=True,
            entity_memory=memory,
            verbose=True,
        )

        result = await crew.kickoff_async()
        return result
    finally:
        for adpater in mcp_adapter:
            try: 
                adpater.stop()
            except Exception:
                pass

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
    #mcp.run()