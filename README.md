📚 Books_Explorer

Books_Explorer is a portal where users can log in, chat with an agent, and explore books based on their preferences. The agent asks clarifying questions, then displays matching books along with options to buy and choose delivery modes.

🚀 Features

🔑 User login system

💬 Chat with agent to describe book requirements

❓ Smart query handling (agent asks for more details)

📖 Book search & recommendation

🛒 Buying options with delivery modes

⚙️ Installation & Setup
1. Install Dependencies

Create and activate a virtual environment (recommended), then install requirements:

pip install streamlit requests python-dotenv

2. Setup API Key

Create a .env file in the project root with your Google Books API key:

GOOGLE_BOOKS_API_KEY=your_api_key_here

3. Run the Application
python -m streamlit run app.py


Once running, open the link provided by Streamlit (usually http://localhost:8501) 🎉
