"""
Enricher module for Hashnode API integration.

Fetches additional data from Hashnode GraphQL API to enrich posts with
tag names, series descriptions, and other metadata.
"""

import os
import requests
from typing import Dict, List, Optional, Any
from rich.console import Console

console = Console()


class HashNodeEnricher:
    """Enriches export data using Hashnode GraphQL API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize enricher with API key."""
        self.api_key = api_key or os.getenv('HASHNODE_API_KEY')
        self.base_url = 'https://gql.hashnode.com'
        
    def can_enrich(self) -> bool:
        """Check if enrichment is possible (API key available)."""
        return bool(self.api_key)
        
    def enrich_posts(self, post_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Enrich multiple posts with API data."""
        if not self.can_enrich():
            console.print("[yellow]No API key available, skipping enrichment[/yellow]")
            return {}
            
        console.print(f"[blue]Enriching {len(post_ids)} posts from Hashnode API...[/blue]")
        
        enriched_data = {}
        
        # Process posts in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(post_ids), batch_size):
            batch = post_ids[i:i + batch_size]
            console.print(f"[blue]Processing batch {i//batch_size + 1} ({len(batch)} posts)...[/blue]")
            
            for post_id in batch:
                try:
                    post_data = self._fetch_post_data(post_id)
                    if post_data:
                        enriched_data[post_id] = post_data
                except Exception as e:
                    console.print(f"[red]Failed to fetch data for post {post_id}: {e}[/red]")
                    continue
                    
        console.print(f"[green]Successfully enriched {len(enriched_data)} posts[/green]")
        return enriched_data
        
    def enrich_publication_series(self, publication_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch series data for a publication."""
        if not self.can_enrich():
            return {}
            
        try:
            query = """
            query GetPublicationSeries($id: ID!) {
                publication(id: $id) {
                    seriesList(first: 100) {
                        edges {
                            node {
                                id
                                name
                                slug
                                description {
                                    text
                                }
                            }
                        }
                    }
                }
            }
            """
            
            variables = {"id": publication_id}
            response = self._make_request(query, variables)
            
            if not response or 'data' not in response:
                return {}
                
            series_data = {}
            series_list = response['data'].get('publication', {}).get('seriesList', {}).get('edges', [])
            
            for edge in series_list:
                series = edge['node']
                series_data[series['id']] = {
                    'id': series['id'],
                    'name': series['name'],
                    'slug': series['slug'],
                    'description': series.get('description', {}).get('text', '')
                }
                
            console.print(f"[green]Found {len(series_data)} series[/green]")
            return series_data
            
        except Exception as e:
            console.print(f"[red]Failed to fetch series data: {e}[/red]")
            return {}
            
    def _fetch_post_data(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Fetch enriched data for a single post."""
        query = """
        query GetPost($id: ID!) { 
            post(id: $id) { 
                id title 
                tags { id name slug } 
                series { id name description { text } coverImage } 
                coverImage { url attribution } 
                publication { id title } 
            } 
        }
        """
        
        variables = {"id": post_id}
        response = self._make_request(query, variables)
        
        if not response or 'data' not in response:
            return None
            
        post_data = response['data'].get('post')
        if not post_data:
            console.print(f"[yellow]No data returned for post {post_id}[/yellow]")
            return None
            
        # Transform to match expected structure
        return {
            'id': post_data['id'],
            'title': post_data['title'],
            'slug': '',  # Not available from API, will use from original export
            'brief': '',  # Not available from API, will use from original export
            'content': {},  # Not available from API, will use from original export
            'tags': post_data.get('tags', []),
            'series': post_data.get('series'),
            'coverImage': post_data.get('coverImage'),
            'publication': post_data.get('publication'),
            'readTimeInMinutes': 5  # Default value, not available from API
        }
        
    def _make_request(self, query: str, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make GraphQL request to Hashnode API."""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        payload = {
            'query': query,
            'variables': variables
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'errors' in data:
                console.print(f"[red]GraphQL errors: {data['errors']}[/red]")
                return None
                
            return data
            
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Request failed: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Unexpected error: {e}[/red]")
            return None
            
    def create_fallback_enrichment(self, posts: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Create basic enriched data structure when API is not available."""
        console.print("[yellow]Creating fallback enrichment without API data[/yellow]")
        
        enriched_data = {}
        
        for post in posts:
            post_id = post['_id']
            
            # Create basic structure using export data
            enriched_data[post_id] = {
                'id': post_id,
                'title': post.get('title', ''),
                'slug': post.get('slug', ''),
                'brief': post.get('brief', ''),
                'content': {
                    'html': post.get('content', ''),
                    'markdown': post.get('contentMarkdown', post.get('content', ''))
                },
                'tags': self._create_fallback_tags(post.get('tags', [])),
                'series': self._create_fallback_series(post.get('series')),
                'coverImage': {'url': post.get('coverImage')} if post.get('coverImage') else None,
                'publishedAt': post.get('publishedAt', post.get('dateAdded')),
                'readTimeInMinutes': post.get('readTimeInMinutes', 5)
            }
            
        console.print(f"[yellow]Created fallback data for {len(enriched_data)} posts[/yellow]")
        console.print("[yellow]Note: Tags will show as IDs, series info may be limited[/yellow]")
        
        return enriched_data
        
    def _create_fallback_tags(self, tag_ids: List[str]) -> List[Dict[str, str]]:
        """Create fallback tag structure with IDs only."""
        return [
            {
                'id': tag_id,
                'name': f'Tag-{tag_id[:8]}',  # Use first 8 chars of ID as name
                'slug': f'tag-{tag_id[:8]}'
            }
            for tag_id in tag_ids
        ]
        
    def _create_fallback_series(self, series_id: Optional[str]) -> Optional[Dict[str, str]]:
        """Create fallback series structure if series ID exists."""
        if not series_id:
            return None
            
        return {
            'id': series_id,
            'name': f'Series-{series_id[:8]}',
            'slug': f'series-{series_id[:8]}',
            'description': ''
        }