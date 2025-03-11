import streamlit as st
import requests
import openai
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Get users from environment variable
# Remove this line
# from config import USERS

# Keep the environment variable approach
USERS = json.loads(os.getenv('AUTHORIZED_USERS', '{}'))

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["username"] in USERS:
            if st.session_state["password"] == USERS[st.session_state["username"]]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # Don't store password
                st.success("Logged in successfully")
            else:
                st.session_state["password_correct"] = False
                st.error("Invalid password")
    
    if "password_correct" not in st.session_state:
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        st.button("Login", on_click=password_entered)
        return False
    
    return st.session_state["password_correct"]

# Authentication check
if not check_password():
    st.stop()

# API Keys
NINJA_API_KEY = os.getenv('NINJA_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configure OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# List of companies
companies = {
    'MSFT': 'Microsoft',
    'GOOGL': 'Alphabet',
    'META': 'Meta',
    'AMZN': 'Amazon',
    'CSCO': 'Cisco Systems',
    'ERIC': 'Ericsson',
    'NOK': 'Nokia',
    'JNPR': 'Juniper',
    'PANW': 'Palo Alto Networks',
    'NVDA': 'Nvidia',
    'ANET': 'Arista'
}

fiscal_year_ends = {
    'MSFT': 6, 'GOOGL': 12, 'META': 12, 'AMZN': 12, 'CSCO': 7,
    'ERIC': 12, 'NOK': 12, 'JNPR': 12, 'PANW': 7, 'NVDA': 1, 'ANET': 12
}

def get_last_reported_quarter():
    """Get the last reported calendar quarter and corresponding year."""
    current_month = datetime.now().month
    current_year = datetime.now().year
    last_calendar_quarter = (current_month - 1) // 3
    if last_calendar_quarter == 0:
        return 4, current_year - 1
    return last_calendar_quarter, current_year

def get_fiscal_quarter_and_year(company_ticker, calendar_quarter, calendar_year):
    """Convert calendar quarter to fiscal quarter and year."""
    fiscal_year_end = fiscal_year_ends.get(company_ticker, 12)
    if fiscal_year_end != 12:
        fiscal_year = calendar_year + 1 if calendar_quarter * 3 > fiscal_year_end else calendar_year
    else:
        fiscal_year = calendar_year
    fiscal_quarter = ((calendar_quarter - (fiscal_year_end // 3) + 3) % 4) + 1
    return fiscal_quarter, fiscal_year

def get_earnings_transcript(ticker, year, quarter):
    """Fetch earnings transcript from API Ninjas."""
    api_url = f'https://api.api-ninjas.com/v1/earningstranscript?ticker={ticker}&year={year}&quarter={quarter}'
    response = requests.get(api_url, headers={'X-Api-Key': NINJA_API_KEY})
    if response.status_code == 200:
        data = response.json()
        # Handle both list and dictionary responses
        if isinstance(data, list):
            return data[0].get('transcript', 'No transcript available.') if data else 'No transcript available.'
        return data.get('transcript', 'No transcript available.')
    return f"Error fetching transcript: {response.status_code}"

def analyze_transcript(company_name, transcript, search_query):
    try:
        if not transcript or not isinstance(transcript, str):
            return "Error: Invalid or empty transcript"
            
        cleaned_transcript = transcript.strip()
        if not cleaned_transcript:
            return "Error: Empty transcript"
            
        max_tokens = 16000 if search_query == "General Overview" else 16000
        
        # Enhanced prompt for specific analysis
        base_prompt = f"""Analyze this {company_name} earnings call transcript specifically focusing on {search_query}.

        Requirements:
        1. Extract and analyze ONLY information related to {search_query}
        2. Include specific numbers, metrics, and direct quotes where relevant
        3. Highlight key strategic decisions and future plans
        4. Compare with previous quarters if mentioned
        5. Focus on concrete details rather than general statements

        Format your response as:
        • Key Findings (with specific metrics, quotes and examples wherever available)
        
        Transcript: {cleaned_transcript[:50000]}"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a specialized financial analyst focusing on technology sector earnings. Provide detailed, data-driven analysis with specific metrics and quotes. Avoid generic statements. If certain information is not available in the transcript, explicitly state that."},
                    {"role": "user", "content": base_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0
            )
            
            if not response or not hasattr(response, 'choices') or not response.choices:
                return "Error: Invalid response from OpenAI"
                
            return response.choices[0].message.content
            
        except openai.AuthenticationError as auth_error:
            return f"OpenAI Authentication Error: {str(auth_error)}"
        except openai.APIError as api_error:
            return f"OpenAI API Error: {str(api_error)}"
            
    except Exception as e:
        return f"Error analyzing transcript: {str(e)}"

def get_executive_summary(summaries, search_query):
    """Generate a context-aware executive summary based on search query"""
    combined_text = "\n\n".join([f"{company}: {summary}" for company, summary in summaries.items()])
    
    if search_query == "General Overview":
        prompt = """Create a comprehensive executive summary of these technology companies' earnings. Focus on:
        1. Key market trends across companies
        2. Common themes in AI and technology initiatives
        3. Overall market sentiment
        4. Notable concerns or challenges
        
        Format as bullet points with specific metrics and examples."""
    else:
        prompt = f"""Create a focused executive summary specifically about {search_query} across these technology companies. Be as conscise as possible. Focus on:
        1. Common patterns and trends related to {search_query} and provide data points, quotes and examples wherever available 
        2. Key differences in how companies approach {search_query} and provide data points, quotes and examples wherever available
        4. Future plans and strategies related to {search_query} and provide data points, quotes and examples wherever available
        
        Format as bullet points with specific examples and metrics."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a senior financial analyst. Provide concise, data-driven insights focusing specifically on the requested analysis topic."},
                {"role": "user", "content": f"{prompt}\n\nAnalyses:\n{combined_text}"}
            ],
            max_tokens=1000,
            temperature=0
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating executive summary: {str(e)}"

# Streamlit UI
st.title("Earnings Transcript Analyzer")

# Multiple company selection
selected_companies = st.multiselect(
    "Select companies:",
    options=list(companies.keys()),
    format_func=lambda x: companies[x],
    default=[list(companies.keys())[0]]
)

# Search query input
search_options = [
    "General Overview",
    "Custom Query"
]
search_type = st.selectbox("What would you like to analyze?", search_options)

# Show custom query input if selected
if search_type == "Custom Query":
    search_query = st.text_input("Enter topic to search across common patterns, key differences, future plans:")
else:
    search_query = search_type

if st.button("Analyze"):
    last_calendar_quarter, last_calendar_year = get_last_reported_quarter()
    company_summaries = {}
    
    # Collect all analyses first
    for selected_company in selected_companies:
        with st.spinner(f"Analyzing {companies[selected_company]}..."):
            fiscal_quarter, fiscal_year = get_fiscal_quarter_and_year(
                selected_company, 
                last_calendar_quarter, 
                last_calendar_year
            )
            
            transcript = get_earnings_transcript(selected_company, fiscal_year, fiscal_quarter)
            if "Error" not in transcript:
                summary = analyze_transcript(companies[selected_company], transcript, search_query)
                company_summaries[companies[selected_company]] = summary
            else:
                company_summaries[companies[selected_company]] = transcript
    
    # Display context-aware executive summary first
    if company_summaries:
        st.header("Executive Summary")
        exec_summary = get_executive_summary(company_summaries, search_query)
        st.write(exec_summary)
        st.divider()
    
    # Display individual company analyses
    for selected_company in selected_companies:
        st.subheader(f"Analysis for {companies[selected_company]}")
        if companies[selected_company] in company_summaries:
            st.write(company_summaries[companies[selected_company]])
        st.divider()

