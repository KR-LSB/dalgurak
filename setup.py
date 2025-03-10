from setuptools import setup, find_packages

setup(
    name="dalgurak-ai",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'langchain',
        'langchain-openai',
        'langchain-chroma',
        'openai',
        'python-dotenv',
        'aiohttp',
        'pytest',
        'pytest-asyncio',
        'psutil'
    ]
)