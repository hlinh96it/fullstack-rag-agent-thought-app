import requests

from sqlalchemy import URL, engine
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.chat_models import init_chat_model

from dotenv import load_dotenv
load_dotenv()

from src.config import Settings

settings = Settings()


databases = []

response = requests.get(
    url='http://127.0.0.1:8000/postgres/databases/6909b78f41dca376afd84862'
)
list_database = response.json().get('databases', [])

for database in list_database:
    url = URL.create(
        drivername=settings.postgres_db.driver_name,
        username=settings.postgres_db.username,
        password=settings.postgres_db.password,
        host=settings.postgres_db.host, port=settings.postgres_db.port,
        database=database['database_name']
    )
    engine = create_engine(
        url=url,
        echo=False,
        pool_size=settings.postgres_db.pool_size,
        max_overflow=settings.postgres_db.max_overflow,
        pool_pre_ping=True,
    )
    
    databases.append({
        'name': database['database_name'], 'database': SQLDatabase(engine)
    })
    
llm = init_chat_model(model='gpt-5-mini', model_provider='openai')
toolkit = SQLDatabaseToolkit(llm=llm, db=databases[0]['database'])
tools = toolkit.get_tools()

for tool in tools:
    print(f"{tool.name}: {tool.description}\n")
    
    



    
