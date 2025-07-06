"""
Parser module for Hashnode exports.

Handles loading and validating Hashnode JSON export files.
"""

import json
import os
from typing import Dict, List, Optional, Any
from rich.console import Console

console = Console()


class HashNodeParser:
    """Parser for Hashnode export files."""
    
    def __init__(self, export_path: str):
        """Initialize parser with export file path."""
        self.export_path = export_path
        self.export_data: Optional[Dict[str, Any]] = None
        self._posts: List[Dict[str, Any]] = []
        self._publication_info: Optional[Dict[str, Any]] = None
        
    def load_export(self) -> None:
        """Load and validate the export file."""
        if not os.path.exists(self.export_path):
            raise FileNotFoundError(f"Export file not found: {self.export_path}")
            
        try:
            with open(self.export_path, 'r', encoding='utf-8') as f:
                self.export_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in export file: {e}")
        except Exception as e:
            raise ValueError(f"Error reading export file: {e}")
            
        self._validate_export()
        self._extract_data()
        
    def _validate_export(self) -> None:
        """Validate the export data structure."""
        if not isinstance(self.export_data, dict):
            raise ValueError("Export data must be a JSON object")
            
        if 'posts' not in self.export_data:
            raise ValueError("Export data must contain 'posts' array")
            
        if not isinstance(self.export_data['posts'], list):
            raise ValueError("'posts' must be an array")
            
        if len(self.export_data['posts']) == 0:
            console.print("[yellow]Warning: No posts found in export[/yellow]")
            
    def _extract_data(self) -> None:
        """Extract posts and publication info from export data."""
        self._posts = self.export_data.get('posts', [])
        self._publication_info = self.export_data.get('publication', {})
        
        # Validate individual posts
        valid_posts = []
        for i, post in enumerate(self._posts):
            if self._validate_post(post, i):
                valid_posts.append(post)
                
        self._posts = valid_posts
        console.print(f"[green]Loaded {len(self._posts)} valid posts[/green]")
        
    def _validate_post(self, post: Dict[str, Any], index: int) -> bool:
        """Validate individual post structure."""
        required_fields = ['_id', 'title', 'slug']
        
        for field in required_fields:
            if field not in post:
                console.print(f"[red]Warning: Post {index} missing required field '{field}', skipping[/red]")
                return False
                
        # Ensure basic data types
        if not isinstance(post.get('title'), str):
            console.print(f"[red]Warning: Post {index} has invalid title, skipping[/red]")
            return False
            
        if not isinstance(post.get('slug'), str):
            console.print(f"[red]Warning: Post {index} has invalid slug, skipping[/red]")
            return False
            
        return True
        
    def get_posts(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get posts, optionally limited to a specific number."""
        if self._posts is None:
            raise RuntimeError("Must call load_export() first")
            
        posts = self._posts
        if limit is not None:
            posts = posts[:limit]
            if limit < len(self._posts):
                console.print(f"[yellow]Limited to {limit} posts (of {len(self._posts)} total)[/yellow]")
                
        return posts
        
    def get_post_ids(self, limit: Optional[int] = None) -> List[str]:
        """Get list of post IDs."""
        posts = self.get_posts(limit)
        return [post['_id'] for post in posts]
        
    def get_publication_info(self) -> Dict[str, Any]:
        """Get publication information."""
        if self._publication_info is None:
            raise RuntimeError("Must call load_export() first")
            
        return self._publication_info
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the export data."""
        if self._posts is None:
            raise RuntimeError("Must call load_export() first")
            
        post_ids = [post['_id'] for post in self._posts[:5]]  # First 5 IDs
        
        return {
            'total_posts': len(self._posts),
            'publication_id': self._publication_info.get('_id', 'unknown'),
            'publication_title': self._publication_info.get('title', 'Unknown'),
            'post_ids': post_ids,
            'has_more_posts': len(self._posts) > 5
        }
        
    def get_all_tags(self) -> List[str]:
        """Get all unique tag IDs from posts."""
        if self._posts is None:
            raise RuntimeError("Must call load_export() first")
            
        tag_ids = set()
        for post in self._posts:
            tags = post.get('tags', [])
            if isinstance(tags, list):
                tag_ids.update(tags)
                
        return list(tag_ids)
        
    def get_all_series(self) -> List[str]:
        """Get all unique series IDs from posts."""
        if self._posts is None:
            raise RuntimeError("Must call load_export() first")
            
        series_ids = set()
        for post in self._posts:
            series = post.get('series')
            if series and isinstance(series, str):
                series_ids.add(series)
                
        return list(series_ids)