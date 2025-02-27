import streamlit as st
import requests
import pandas as pd
import datetime
import time
import xml.etree.ElementTree as ET
import re
from dateutil import parser

# Set page configuration
st.set_page_config(
    page_title="ArXiv AI Safety & Governance Explorer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add custom CSS for better styling
st.markdown("""
<style>
    .paper-title {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .paper-authors {
        font-size: 14px;
        color: #505050;
        margin-bottom: 5px;
    }
    .paper-date {
        font-size: 12px;
        color: #707070;
        margin-bottom: 10px;
    }
    .paper-abstract {
        font-size: 14px;
        margin-bottom: 10px;
        text-align: justify;
    }
    .paper-categories {
        font-size: 12px;
        color: #606060;
        margin-bottom: 15px;
    }
    .paper-link {
        font-size: 14px;
        margin-bottom: 20px;
    }
    hr {
        margin-top: 30px;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar title and description
st.sidebar.title("Search Parameters")
st.sidebar.markdown("Configure your search for AI Safety & Governance papers")

# Define topic categories with descriptions
TOPIC_CATEGORIES = {
    "AI Safety": "Technical safety, alignment, robustness, interpretability",
    "AI Governance": "Policy, regulation, standards, international cooperation",
    "AI Ethics": "Fairness, accountability, transparency, ethical considerations",
    "Societal Impacts": "Economic impacts, labor market effects, social implications",
    "Long-term AI": "Existential risk, transformative AI scenarios",
    "Technical Governance": "Auditing, red-teaming, evaluation methods",
}

# Define ArXiv categories relevant to our topics
ARXIV_CATEGORIES = [
    "cs.AI", "cs.CY", "cs.LG", "cs.CL", "cs.RO", "cs.HC", 
    "stat.ML", "econ.GN", "q-fin.EC"
]

# Main title
st.title("ArXiv AI Safety & Governance Explorer")
st.markdown("Discover the latest research on AI safety, governance, and their societal implications")

# Topic selection in sidebar
st.sidebar.subheader("Topics of Interest")
selected_topics = {}
for topic, description in TOPIC_CATEGORIES.items():
    selected_topics[topic] = st.sidebar.checkbox(
        f"{topic}", 
        value=True, 
        help=f"{description}"
    )

# Date range selection
st.sidebar.subheader("Date Range")
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=90)  # Default to last 90 days
date_range = st.sidebar.slider(
    "Select date range",
    min_value=end_date - datetime.timedelta(days=365),
    max_value=end_date,
    value=(start_date, end_date),
    format="YYYY-MM-DD",
)

# Sort options
st.sidebar.subheader("Sorting")
sort_by = st.sidebar.radio(
    "Sort results by:",
    options=["Relevance", "Date (Newest First)", "Date (Oldest First)"],
    index=1,
)

# Advanced search options
st.sidebar.subheader("Advanced Options")
with st.sidebar.expander("Advanced Search Settings"):
    max_results = st.slider("Maximum number of results", 10, 200, 50)
    include_abstracts = st.checkbox("Include Abstracts in Search", value=True)
    selected_categories = st.multiselect(
        "ArXiv Categories",
        options=ARXIV_CATEGORIES,
        default=ARXIV_CATEGORIES,
        help="Select specific ArXiv categories to search within"
    )

# Search bar
st.subheader("Search Papers")
search_query = st.text_input("Enter keywords or phrases", "")

# Function to create search query strings for ArXiv API
def build_arxiv_query():
    # Start with an empty query
    query_parts = []
    
    # Add user search terms if provided
    if search_query:
        # Clean up the search query
        cleaned_query = search_query.strip()
        # Add the user's search terms
        if include_abstracts:
            query_parts.append(f"(ti:{cleaned_query} OR abs:{cleaned_query})")
        else:
            query_parts.append(f"ti:{cleaned_query}")
    
    # Add topic-specific search terms based on user selection
    topic_terms = []
    
    if selected_topics["AI Safety"]:
        safety_terms = ["safety", "alignment", "robustness", "interpretability", 
                      "explainability", "transparency", "reliable", "trustworthy"]
        topic_terms.extend(safety_terms)
    
    if selected_topics["AI Governance"]:
        governance_terms = ["governance", "policy", "regulation", "standard", 
                          "compliance", "oversight", "guideline"]
        topic_terms.extend(governance_terms)
    
    if selected_topics["AI Ethics"]:
        ethics_terms = ["ethics", "fairness", "bias", "discrimination", 
                       "accountability", "responsibility", "moral"]
        topic_terms.extend(ethics_terms)
    
    if selected_topics["Societal Impacts"]:
        societal_terms = ["economic impact", "labor market", "job", "employment", 
                        "inequality", "social impact", "society"]
        topic_terms.extend(societal_terms)
    
    if selected_topics["Long-term AI"]:
        longterm_terms = ["existential risk", "x-risk", "long-term", "AGI", 
                        "artificial general intelligence", "superintelligence"]
        topic_terms.extend(longterm_terms)
    
    if selected_topics["Technical Governance"]:
        tech_gov_terms = ["audit", "evaluation", "assessment", "red team", 
                        "benchmark", "testing", "monitor"]
        topic_terms.extend(tech_gov_terms)
    
    # Add topic terms to query if any are selected
    if topic_terms:
        topic_query = " OR ".join([f'"{term}"' for term in topic_terms])
        if include_abstracts:
            query_parts.append(f"(ti:({topic_query}) OR abs:({topic_query}))")
        else:
            query_parts.append(f"ti:({topic_query})")
    
    # Add category constraints
    if selected_categories:
        cat_query = " OR ".join([f"cat:{cat}" for cat in selected_categories])
        query_parts.append(f"({cat_query})")
    
    # Add date range
    start_date_str = date_range[0].strftime("%Y%m%d")
    end_date_str = date_range[1].strftime("%Y%m%d")
    query_parts.append(f"submittedDate:[{start_date_str}0000 TO {end_date_str}2359]")
    
    # Combine all parts with AND
    final_query = " AND ".join([f"({part})" for part in query_parts])
    
    return final_query

# Function to fetch papers from ArXiv API
def fetch_arxiv_papers(query, max_results=50, sort_by="submittedDate"):
    base_url = "http://export.arxiv.org/api/query?"
    
    # Define sorting parameter
    sort_mapping = {
        "Relevance": "relevance",
        "Date (Newest First)": "submittedDate",
        "Date (Oldest First)": "submittedDate",
    }
    sort_order = "descending" if sort_by != "Date (Oldest First)" else "ascending"
    
    # Construct the query URL
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": sort_mapping.get(sort_by, "submittedDate"),
        "sortOrder": sort_order,
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = base_url + query_string
    
    try:
        response = requests.get(full_url)
        response.raise_for_status()  # Raise exception for HTTP errors
        return response.text
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching papers: {str(e)}")
        return None

# Function to parse ArXiv API XML response
def parse_arxiv_response(xml_data):
    if xml_data is None:
        return []
    
    try:
        # Parse XML
        root = ET.fromstring(xml_data)
        
        # Define namespace
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        
        papers = []
        
        # Extract each entry (paper)
        for entry in root.findall(".//atom:entry", ns):
            try:
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                
                # Extract authors
                authors = []
                for author in entry.findall(".//atom:author/atom:name", ns):
                    if author.text:
                        authors.append(author.text.strip())
                
                # Join authors with commas
                authors_str = ", ".join(authors)
                
                # Extract abstract
                abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
                
                # Extract publication date
                published = entry.find("atom:published", ns).text
                pub_date = parser.parse(published).strftime("%Y-%m-%d")
                
                # Extract link
                link = ""
                for link_tag in entry.findall("atom:link", ns):
                    if link_tag.get("title") == "pdf":
                        link = link_tag.get("href")
                        break
                
                # If no PDF link found, use the DOI or abstract link
                if not link:
                    link = entry.find("atom:id", ns).text
                
                # Extract categories
                categories = []
                for cat in entry.findall("atom:category", ns):
                    cat_term = cat.get("term")
                    if cat_term:
                        categories.append(cat_term)
                
                # Join categories with commas
                categories_str = ", ".join(categories)
                
                # Extract DOI if available
                doi = ""
                for link_tag in entry.findall("atom:link", ns):
                    if link_tag.get("title") == "doi":
                        doi = link_tag.get("href")
                        break
                
                # Create paper dictionary
                paper = {
                    "title": title,
                    "authors": authors_str,
                    "abstract": abstract,
                    "pub_date": pub_date,
                    "link": link,
                    "categories": categories_str,
                    "doi": doi
                }
                
                papers.append(paper)
            except Exception as e:
                st.warning(f"Error parsing a paper entry: {str(e)}")
                continue
        
        return papers
    except Exception as e:
        st.error(f"Error parsing ArXiv response: {str(e)}")
        return []

# Function to check if a paper matches the selected topics
def paper_matches_topics(paper, selected_topics):
    # If no topics are selected, return all papers
    if not any(selected_topics.values()):
        return True
    
    # Define keywords for each topic
    topic_keywords = {
        "AI Safety": ["safety", "alignment", "robustness", "interpretability", 
                     "explainability", "transparent", "reliable", "trustworthy"],
        
        "AI Governance": ["governance", "policy", "regulation", "standard", 
                         "compliance", "oversight", "guideline"],
        
        "AI Ethics": ["ethics", "fairness", "bias", "discrimination", 
                     "accountability", "responsibility", "moral"],
        
        "Societal Impacts": ["economic", "labor", "job", "employment", 
                           "inequality", "social impact", "society"],
        
        "Long-term AI": ["existential", "x-risk", "long-term", "AGI", 
                        "general intelligence", "superintelligence"],
        
        "Technical Governance": ["audit", "evaluation", "assessment", "red team", 
                               "benchmark", "testing", "monitor"]
    }
    
    # Check title and abstract for each selected topic
    text_to_check = (paper["title"] + " " + paper["abstract"]).lower()
    
    for topic, is_selected in selected_topics.items():
        if is_selected:
            keywords = topic_keywords.get(topic, [])
            for keyword in keywords:
                if keyword.lower() in text_to_check:
                    return True
    
    return False

# Function to display a single paper
def display_paper(paper):
    st.markdown(f"<div class='paper-title'>{paper['title']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='paper-authors'>{paper['authors']}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='paper-date'>Published: {paper['pub_date']}</div>", unsafe_allow_html=True)
    
    with st.expander("Abstract"):
        st.markdown(f"<div class='paper-abstract'>{paper['abstract']}</div>", unsafe_allow_html=True)
    
    st.markdown(f"<div class='paper-categories'>Categories: {paper['categories']}</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(f"<a href='{paper['link']}' target='_blank'>View Paper</a>", unsafe_allow_html=True)
    
    # Add a separator line
    st.markdown("<hr/>", unsafe_allow_html=True)

# Search button
if st.button("Search ArXiv"):
    with st.spinner("Fetching papers from ArXiv..."):
        # Build the query
        query = build_arxiv_query()
        
        # For debugging
        st.sidebar.expander("Debug: Query String").write(query)
        
        # Fetch papers
        xml_data = fetch_arxiv_papers(query, max_results, sort_by)
        
        # Parse the response
        all_papers = parse_arxiv_response(xml_data)
        
        # Apply additional filtering if needed
        matched_papers = [p for p in all_papers if paper_matches_topics(p, selected_topics)]
        
        # Display the results
        if matched_papers:
            st.success(f"Found {len(matched_papers)} papers matching your criteria")
            
            # Display each paper
            for paper in matched_papers:
                display_paper(paper)
        else:
            st.info("No papers found matching your criteria. Try broadening your search parameters.")

# Add information about the app
with st.expander("About this Application"):
    st.markdown("""
    **ArXiv AI Safety & Governance Explorer** is a tool for researchers, policymakers, and anyone interested 
    in the latest research on AI safety, governance, ethics, and societal impacts.
    
    The app searches the [ArXiv](https://arxiv.org/) database for papers related to:
    
    - **AI Safety**: Technical safety, alignment, robustness, interpretability
    - **AI Governance**: Policy, regulation, standards, international cooperation
    - **AI Ethics**: Fairness, accountability, transparency
    - **Societal Impacts**: Economic impacts, labor market effects, social implications
    - **Long-term AI**: Existential risk, transformative AI scenarios
    - **Technical Governance**: Auditing, red-teaming, evaluation methods
    
    Papers are fetched directly from the ArXiv API and filtered based on your search criteria.
    """)
