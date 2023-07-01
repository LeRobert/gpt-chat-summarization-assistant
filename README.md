# GPT Chat and Summarization Assistant

**Chat with your own assistant that takes on different personalities or request it so summarize arbitrarily long PDF files or web pages.**

GPT Chat and Summarization Assistant is a Python web app (using [Dash framework](https://github.com/plotly/dash)) made to be easy and flexible to use. You can put a personality on it and have a nice discussion. By setting the randomness factor you can influence the "creativity" of responses. 
The AI Assistant can summarize an arbitrarily long PDF file or a web page - as an ordinary textual summary, as bullets or with a focus on a specific question.

## Usage

**Install**

- `git clone https://github.com/LeRobert/gpt-chat-summarization-assistant.git`
- create a virtual environment, e.g. with `py -m venv .\venv`
- activate the virtual environment, e.g. with `.\venv\Scripts\activate.bat`
- install required libraries with `pip install -r requirements.txt`
- rename .env-template to .env, insert your OpenAI API key

**Setup**

In .env file:
- insert your OpenAI API key:
  - `OPENAI_API_KEY=[your api key]`

In app.py:
- Select the GPT model
  - LLM_MODEL = "gpt-4" (default) or "gpt-3.5-turbo"
- Set the maximum number of tokens for summarization of a single chunk of a document/web page:
  - MAX_TOKENS_PER_CHUNK = 7000 (for gpt-4) or e.g. 1500 for gpt-3.5-turbo

**Run**:

Run the assistant with `python app.py` and click on the link in the terminal.

By running GPT Chat and Summarization Assistant you agree to our [disclaimer](https://github.com/LeRobert/gpt-chat-summarization-assistant/blob/main/DISCLAIMER.md).

## Features

- Set the personality of the AI Assistant from preset personalities - or describe a custom one
- Modify the randomness of text generation
- Equations provided in response are rendered with LaTeX
- Response is formatted with markdown
- Summarize an arbitrarily long PDF or webpage.
- Select a summarization form - text summary, bullet points, focus on question
- Download a current conversation or a summary

## Contributing

Anyone with a good idea is welcome to contribute to this project!
