# Author: Robert Leskovar (robert.leskovar@gmail.com), 2023
# Main Dash app

import base64
import dash.exceptions
from dotenv import load_dotenv
import os
import io
import openai
import re
from dash import Dash, dcc, html, Input, Output, State, ctx, DiskcacheManager, clientside_callback, ClientsideFunction
import dash_bootstrap_components as dbc
from utils.consts import AI_ROLE_OPTIONS_EN, AI_SUMMARIZATION_TYPE
from utils.openai_mgmt import openai_completion
from utils.text_extract_summarize import retrieve_pdf_from_response, extract_text_from_pdf, \
    process_text, page_to_string, get_content_from_url
from dash_auth import BasicAuth
import diskcache

# cache is required for a long-running call to OpenAI's API
cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

# OpenAI's model to use for discussion and summarization via API. Recommended are gpt-4 or gpt-3.5-turbo
LLM_MODEL = "gpt-4"

# Max number of tokens for summarization of a single chunk of a document/web page.
# gpt-4 has a limit of 8192 tokens, gpt-3.5-turbo has a limit of 2048 tokens. (as of June 2023)
# Use a lower value than the limit.
MAX_TOKENS_PER_CHUNK = 7000

DEFAULT_UPLOAD_CONTENT = [
    'Drag and Drop or ',
    html.B('Select Files')
]


def get_system_prompt(sys_prompt, ai_custom_role):
    if ai_custom_role is not None and len(ai_custom_role) > 0:
        system_prompt = f"You are {ai_custom_role}."
    else:
        system_prompt = f"You are {sys_prompt}."

    if any(subs in system_prompt for subs in ["school", "physics", "math", "maths", "mathematics"]):
        system_prompt = system_prompt + " If you answer with equations, write them as separate blocks in LaTeX and delimit them with $$."
    elif any(subs in sys_prompt for subs in ["proofreader"]):
        system_prompt += " Proofread and correct this text: "

    return system_prompt


def system_role_UI():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H5('Select AI personality:'),
                dcc.Dropdown(id='sys-prompt',
                             options=AI_ROLE_OPTIONS_EN,
                             value=AI_ROLE_OPTIONS_EN[0],
                             clearable=False,
                             optionHeight=50,
                             ),
            ], width=6),
            dbc.Col([
                html.H5('... or describe a custom one:'),
                dbc.Input(id='ai-custom-role',
                          type='text',
                          placeholder='Describe a custom AI personality',
                          value='',
                          ),
            ]),
        ]),  # end row
    ])  # end div


def main_UI():
    def get_answering_tab():
        return html.Div([
            html.Br(),
            system_role_UI(),
            html.Br(),

            dbc.Row([
                dbc.Col([
                    html.H6('Randomness (0-1.5):'),
                    dbc.Input(id='randomness',
                              type='number',
                              min=0, max=1.5,
                              value=0.8,
                              step=0.1,
                              ),
                ], width=2, align='end'),
                dbc.Col([
                    dbc.Textarea(id='user-text-input',
                                 size="lg",
                                 placeholder="Enter your prompt here.",
                                 key='user-text-input', ),
                ]),
            ]),  # end row
            html.Br(),
            dbc.Row([
                dbc.Col([
                    dbc.Button("Download",
                               id="download-button",
                               className="me-2",
                               n_clicks=0,
                               disabled=False),  # download button
                    dcc.Download(id="download"),  # Download component
                ], width=2),
                dbc.Col([
                    dbc.Button(children="Send prompt",
                               id="prompt-button",
                               className="me-2",
                               n_clicks=0,
                               disabled=False,
                               ),
                ], width=2),
                dbc.Col([
                    dbc.Button(children="Clear history",
                               id="clear-button",
                               className="me-2",
                               n_clicks=0,
                               disabled=False,
                               ),
                ], width=2),
            ]),  # end row
        ])  # end div

    def get_summarization_tab():
        return html.Div([
            html.Br(),
            # row 1
            dbc.Row([
                dbc.Col([
                    html.H5('Summarization Type:'),
                    dcc.Dropdown(
                        id='summ-type',
                        options=list(AI_SUMMARIZATION_TYPE.values()),
                        value=AI_SUMMARIZATION_TYPE["TEXT_SUMMARIZATION"],
                        clearable=False,
                    ),
                ], width=2),  # end col 1
                dbc.Col([
                    html.H5('Load PDF Document:'),
                    dcc.Upload(
                        id='upload-pdf',
                        children=html.Div(DEFAULT_UPLOAD_CONTENT),
                        style={
                            'width': '99%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                            'margin': '10px'
                        },
                        multiple=False
                    ),
                ], width=6),  # end col 2
                dbc.Col([
                    # html.H5('Question (optional):'),
                    dbc.Textarea(id='summ-question',
                                 size="lg",
                                 placeholder="Enter question for summarization to focus on (optional)",
                                 ),
                    # dbc.Input(id='summ-question',
                    #           type='text',
                    #           placeholder='Enter question for summarization to focus on',
                    #           value='',
                    #           ),
                ], align='end'),  # end col 3
            ]),  # end row 1
            # row 2
            dbc.Row([
                dbc.Col([
                    html.H5('Max % of original:'),
                    dbc.Input(id='summ-percent',
                              type='number',
                              min=5, max=90,
                              value=10,
                              step=5,
                              ),
                    html.Br(),
                    dbc.Button("Download",
                               id="download-summ-button",
                               className="me-2",
                               n_clicks=0,
                               disabled=False),  # download button
                    dcc.Download(id="download-summ"),  # Download component

                ], width=2),  # end col 1
                dbc.Col([
                    html.H5('Web address of the PDF file or text page:'),
                    dbc.Input(id='url-input',
                              type='text',
                              placeholder='Enter URL here',
                              value='',
                              ),
                    html.Br(),
                    dbc.Button('Summarize',
                               id='summ-button',
                               className="me-2",
                               n_clicks=0,
                               disabled=False),
                ]),  # end col 2
            ]),  # end row 2
        ])  # end div

    # main_UI body
    return html.Div([
        dcc.Tabs([
            dcc.Tab(label='Answering', children=[
                get_answering_tab()
            ]),
            dcc.Tab(label='Summarization', children=[
                # dbc.Card([get_summarization_tab()])
                get_summarization_tab()
            ])
        ])
    ])  # end div


def output_UI():
    return html.Div([
        dcc.Loading(
            id="loading-api-call",
            type="default",
            # style={'position': 'absolute', 'top': '10px', 'left': '10px'},  # position of spinner
            children=[
                html.Div(id='loading-div'),
            ],
        ),
        html.H4('Output:'),
        html.Div(id='text-output'),
    ])


# instantiate dash
app = Dash(__name__,
           external_stylesheets=[dbc.themes.CERULEAN, r"./assets/styles.css"],
           )  # create layout

server = app.server

app.title = 'GPT Chat and Summarization Assistant'

# # add basic auth (username and password)
# auth = BasicAuth(
#     app,
#     {
#         os.getenv("UNAME"): os.getenv("PASS"),
#         # "test_user": "test_pass",  # enable test user
#     }
# )

app.layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Img(src=r'assets/Title_550px.png', alt='title image'),  # title image
            ], style={'text-align': 'center'}),
        ]),  # header row

        main_UI(), html.Br(),

        output_UI(),

        dcc.Store(id='history'),  # store history of conversation
        dcc.Store(id='outputs'),  # store history of outputs
        dcc.Store(id='summ-outputs'),  # store history of summarization outputs
    ])  # end container
])  # end div


@app.callback(
    Output('text-output', 'children', allow_duplicate=True),
    Output('user-text-input', 'value', allow_duplicate=True),
    Output('history', 'data', allow_duplicate=True),
    Output('outputs', 'data', allow_duplicate=True),

    Input("clear-button", "n_clicks"),
    prevent_initial_call=True,
)
def update_clear_button(clear_button_clicks):
    if clear_button_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise dash.exceptions.PreventUpdate

    trigger_id = ctx.triggered_id
    if 'clear-button' in trigger_id:
        return None, None, [], []


def fix_latex(output_text):
    """
    Check if output_text contains latex content that begins and ends with $$.
    If it does, enclose with newlines every such instance so that it gets render properly.
    """

    def enclose_with_html(match):
        """
        Enclose found LaTeX content with newlines
        """
        latex_content = match.group()[:]
        return f'\n{latex_content}\n'

    # Regex pattern to find LaTeX content beginning and ending with $$
    pattern = re.compile(r'\$\$.*?\$\$', re.DOTALL)

    # Apply enclosing to all matches in the output_text
    output_text = pattern.sub(enclose_with_html, output_text)
    return output_text


@app.callback(
    Output('loading-div', 'children', allow_duplicate=True),
    Output('text-output', 'children', allow_duplicate=True),
    Output('user-text-input', 'value'),
    Output('history', 'data', allow_duplicate=True),
    Output('outputs', 'data', allow_duplicate=True),

    Input('prompt-button', 'n_clicks'),

    State('history', 'data'),
    State('outputs', 'data'),
    State('sys-prompt', 'value'),
    State('ai-custom-role', 'value'),
    State('user-text-input', 'value'),
    State('randomness', 'value'),

    running=[
        (Output("prompt-button", "disabled"), True, False),
        (Output("clear-button", "disabled"), True, False),
        (Output("download-button", "disabled"), True, False),
    ],

    background=True,
    manager=background_callback_manager,
    prevent_initial_call=True,
)
def update_answer_output(prompt_button_clicks, history, outputs, sys_prompt, ai_custom_role, input_text, random_value):
    if prompt_button_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise dash.exceptions.PreventUpdate

    # listen for button clicks
    trigger_id = ctx.triggered_id

    if history is None:
        history = []
    if outputs is None:
        outputs = []

    api_error = False

    # initially, add system prompt to history
    if len(history) == 0:
        system_prompt = get_system_prompt(sys_prompt, ai_custom_role)
        history.append({"role": "system", "content": system_prompt})

    if 'prompt-button' in trigger_id:
        # print(input_text)
        if input_text is None or len(input_text) == 0:
            output_text = 'Please enter a prompt.'
            return html.Div(), dcc.Markdown(output_text, style={'white-space': 'pre-wrap'}), input_text, \
                history, outputs
        else:
            # add user prompt to history and output
            history.append({"role": "user", "content": input_text})

            try:
                output_text = openai_completion(history, LLM_MODEL, random_value)
            except openai.error.OpenAIError as e:
                output_text = f"OpenAI API error: {e}"
                api_error = True
            else:
                # ensure that Latex content is separated in a block (GPT doesn't do it always),
                # to properly render it with MathJax
                output_text = fix_latex(output_text)
                history.append({"role": "assistant", "content": output_text})

            print(f'AI response:\n{output_text}')

            # add output to outputs
            outputs.insert(0, dcc.Markdown('🤖: ' + output_text,
                                           mathjax=True,  # allows for LaTeX formatting
                                           style={'white-space': 'pre-wrap'}))  # keep white space and breaks, wrap
            # add user input to outputs
            outputs.insert(0, dcc.Markdown('\n🙂: ' + input_text, style={'white-space': 'pre-wrap'}))

            # if there was API error, don't clear input text
            if api_error:
                return html.Div(), outputs, input_text, history, outputs
            else:  # otherwise, clear input text
                return html.Div(), outputs, "", history, outputs


def history_to_str(outputs):
    history_str = ""
    # print(outputs)
    for item in outputs:
        # print(item)
        history_str += item.get('props').get('children') + '\n'

    return history_str


@app.callback(
    Output('download', 'data'),

    Input('download-button', 'n_clicks'),

    State('outputs', 'data'),

    prevent_initial_call=True,
)
def update_download(n_clicks, outputs):
    """
    Callback to download the discussion in a text format.
    param: n_clicks: number of clicks on the download button
    param: outputs: the discussion outputs
    return: the download data
    """

    if n_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise dash.exceptions.PreventUpdate

    # listen for button clicks
    trigger_id = ctx.triggered_id

    if 'download-button' in trigger_id and outputs:
        return dict(content=history_to_str(outputs), filename="gpt-discussion.txt")

    return None


@app.callback(
    Output('download-summ', 'data'),

    Input('download-summ-button', 'n_clicks'),

    State('summ-outputs', 'data'),

    prevent_initial_call=True,
)
def update_summ_download(n_clicks, summ_outputs):
    """
    Callback to download the summary text.
    param: n_clicks: number of clicks on the download button
    param: summ_outputs: the summary outputs
    return: the download data
    """
    if n_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise dash.exceptions.PreventUpdate

    # listen for button clicks
    trigger_id = ctx.triggered_id

    if 'download-summ-button' in trigger_id and summ_outputs:
        return dict(content=history_to_str(summ_outputs), filename="gpt-summary.txt")

    return None


@app.callback(
    Output('loading-div', 'children', allow_duplicate=True),
    Output('text-output', 'children', allow_duplicate=True),
    Output('summ-outputs', 'data', allow_duplicate=True),

    Input('summ-button', 'n_clicks'),

    State('upload-pdf', 'contents'),
    State('upload-pdf', 'filename'),
    State('url-input', 'value'),
    State('summ-percent', 'value'),
    State('summ-type', 'value'),
    State('summ-question', 'value'),
    State('randomness', 'value'),
    State('summ-outputs', 'data'),

    running=[
        (Output("summ-button", "disabled"), True, False),
        (Output("download-summ-button", "disabled"), True, False),
    ],

    background=True,
    manager=background_callback_manager,
    prevent_initial_call=True,
)
def update_summarize_output(summ_button_clicks,
                            uploaded_pdf_contents, pdf_filename, url_input, summ_percentage, summ_type, summ_question,
                            randomness, summ_outputs):
    """
    Callback to summarize the text.
    """

    if summ_button_clicks is None:
        # prevent the None callbacks is important with the store component.
        # you don't want to update the store for nothing.
        raise dash.exceptions.PreventUpdate

    summary = ''
    output_string = ''
    url_text = ''
    num_words = 0
    summ_outputs = []

    # listen for button clicks
    trigger_id = ctx.triggered_id

    if 'summ-button' in trigger_id:
        # if URL is provided, use it
        if url_input is not None and len(url_input) > 0:
            try:
                response, content_type = get_content_from_url(url_input)
            except Exception as e:
                output_string = f'HTTP error: {e}'
            else:
                # check if content type is PDF or HTML
                if 'application/pdf' in content_type:
                    try:
                        pdf_object = retrieve_pdf_from_response(response, content_type)
                    except ValueError as e:
                        output_string = f'{e}'
                    else:
                        if pdf_object is not None:
                            url_text, num_words = extract_text_from_pdf(pdf_object)
                        else:
                            output_string = f'Could not extract text from PDF at {url_input}'
                elif 'text/html' in content_type:
                    try:
                        url_text, num_words = page_to_string(response, content_type)
                    except Exception as e:
                        output_string = f'{e}'

                if url_text is not None and len(url_text) > 0:
                    try:
                        summary = process_text(content_text=url_text,
                                               summarize_type=summ_type,
                                               question=summ_question,
                                               llm_model=LLM_MODEL,
                                               tokens_limit=MAX_TOKENS_PER_CHUNK,
                                               length_percentage=summ_percentage,
                                               randomness=randomness)
                    except openai.error.OpenAIError as e:
                        output_string = f"OpenAI API error: {e}"
                    else:
                        if summ_type == AI_SUMMARIZATION_TYPE["FOCUS_QUESTION"]:
                            output_string = f'Summary of the content at {url_input} with {num_words} words to max ' \
                                            f'{summ_percentage}%, focusing on the question "{summ_question}":\n\n{summary}'
                        else:
                            output_string = f'Summary of the content at {url_input} with {num_words} words to max ' \
                                            f'{summ_percentage}%:\n\n{summary}'

        # if URL input field is empty, check if PDF is uploaded
        elif uploaded_pdf_contents is not None:
            content_type, content_string = uploaded_pdf_contents.split(',')

            print(f'{content_type=}')
            print(f'{content_string[:100]=}')

            try:
                pdf_object = base64.b64decode(content_string)
                pdf_object = io.BytesIO(pdf_object)

                if 'pdf' in pdf_filename.lower():
                    pdf_text, num_words = extract_text_from_pdf(pdf_object)
                    try:
                        summary = process_text(content_text=pdf_text,
                                               summarize_type=summ_type,
                                               question=summ_question,
                                               llm_model=LLM_MODEL,
                                               tokens_limit=MAX_TOKENS_PER_CHUNK,
                                               length_percentage=summ_percentage,
                                               randomness=randomness)
                    except openai.error.OpenAIError as e:
                        output_string = f"OpenAI API error: {e}"
            except Exception as e:
                output_string = f'Error processing file {pdf_filename}: {e}'
                print(output_string)
            else:
                if summ_type == AI_SUMMARIZATION_TYPE["FOCUS_QUESTION"]:
                    output_string = f'Summary of the PDF file {pdf_filename} with {num_words} words to max ' \
                                    f'{summ_percentage}%, focusing on the question "{summ_question}":\n\n{summary}'
                else:
                    output_string = f'Summary of the PDF file {pdf_filename} with {num_words} words to max ' \
                                    f'{summ_percentage}%:\n\n{summary}'
        else:
            output_string = 'Please enter a valid URL or upload a PDF.'

        # allows for LaTeX formatting and keep white space and breaks, wrap
        summ_outputs.append(dcc.Markdown('🤖: ' + output_string,
                                         mathjax=True,
                                         style={'white-space': 'pre-wrap'}))

        return html.Div(), summ_outputs, summ_outputs


@app.callback(
    Output('upload-pdf', 'children'),

    Input('upload-pdf', 'filename'),

    prevent_initial_call=True,
)
def update_upload_pdf(filename: str):
    """
    Callback to upload a PDF file.
    """

    upload_text = DEFAULT_UPLOAD_CONTENT.copy()
    upload_text.append(f" ({filename})")
    return upload_text


# run app server
if __name__ == '__main__':
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    app.run_server(debug=True)
