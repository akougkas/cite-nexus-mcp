import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('src'))
from cite_nexus_mcp.tools import find_scholar_id, get_citation

async def main():
    load_dotenv()
    if 'SERPAPI_KEY' in os.environ:
        os.environ['SERP_API_KEY'] = os.environ['SERPAPI_KEY']
        
    print("Finding Scholar ID...")
    res = await find_scholar_id("DLIO benchmark")
    print(res.text)
    
    # Try to extract ID from text
    lines = res.text.split('\n')
    scholar_id = None
    for line in lines:
        if "Found Google Scholar ID:" in line:
            scholar_id = line.split(":")[-1].strip()
            break
            
    if scholar_id:
        print(f"\nExtracted Scholar ID: {scholar_id}")
        print("Getting Citation...")
        citation_res = await get_citation(scholar_id)
        print(citation_res.text)
    else:
        print("Could not extract Scholar ID.")

if __name__ == "__main__":
    asyncio.run(main())
