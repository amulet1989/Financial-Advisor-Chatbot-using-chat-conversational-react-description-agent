import json
import redis
import time
import logging
from langchain.agents import AgentExecutor
from sentence_transformers import CrossEncoder
from src import settings
from src.utils import build_message_history
from src.lang_agent import make_agent
from typing import List, Dict

logging.basicConfig(level=20)

db = redis.Redis(
    host=settings.REDIS_IP, port=settings.REDIS_PORT, db=settings.REDIS_DB_ID
)


def agent_predict(
    agent: AgentExecutor, query: str, chat_history: List[Dict[str, str]]
) -> str:
    """Generate an answer for the given query and chat history using an agent

    Args:
        agent (AgentExecutor): agent to use for QA
        query (str): query to run against the agent
        chat_history (List[Dict[str, str]]): previous message history

    Returns:
        str: answer generated by agent
    """
    try:
        chat_history_ls = build_message_history(chat_history)

        # Run the agent with the query and chat history
        logging.info("Agent running")
        output = agent(
            {
                "input": query,
                "chat_history": chat_history_ls,
            }
        )["output"]

        return output
    except:
        return "I am sorry, I cannot answer at the moment. Please try again later"


def run():
    """Run the model service"""
    # Download cross encoder model for retriever
    logging.info("Downloading cross encoder")
    CrossEncoder("cross-encoder/ms-marco-MiniLM-L-12-v2")

    agent = make_agent()
    logging.info("Waiting for queries...")
    while True:
        _, job_data = db.brpop(settings.REDIS_QUEUE)
        job_data = json.loads(job_data.decode("utf-8"))
        answer = agent_predict(
            agent=agent,
            query=job_data["messages"][-1],
            chat_history=job_data["messages"][:-1],
        )
        out_dict = {"content": answer}
        db.set(job_data["id"], json.dumps(out_dict))

        # Sleep for a bit
        time.sleep(settings.SERVER_SLEEP)


if __name__ == "__main__":
    run()