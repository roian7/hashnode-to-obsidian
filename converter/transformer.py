"""
Content transformer module.

Converts Hashnode post data to 11ty-compatible markdown format with proper frontmatter.
"""

import re
import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from rich.console import Console

console = Console()


class ContentTransformer:
    """Transforms Hashnode content to 11ty format."""
    
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize transformer with template directory."""
        if template_dir is None:
            # Default to templates directory relative to this module
            current_dir = Path(__file__).parent.parent
            template_dir = current_dir / "templates"
            
        self.template_dir = Path(template_dir)
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
    def transform_post(self, original_post: Dict[str, Any], enriched_post: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single post to 11ty format."""
        # Extract content - prefer contentMarkdown, fallback to content
        content = self._get_post_content(original_post, enriched_post)
        
        # Clean and process the content
        cleaned_content = self._clean_content(content)
        
        # Extract and process metadata
        metadata = self._extract_metadata(original_post, enriched_post)
        
        # Create transformed post object
        transformed_post = {
            'title': metadata['title'],
            'slug': metadata['slug'],
            'date': metadata['date'],
            'excerpt': metadata['excerpt'],
            'tags': metadata['tags'],
            'series': metadata['series'],
            'coverImage': metadata['cover_image_url'],
            'readTime': metadata['read_time'],
            'content': cleaned_content,
            'layout': 'post',
            'permalink': f"/{metadata['slug']}/"
        }
        
        return transformed_post
        
    def _get_post_content(self, original_post: Dict[str, Any], enriched_post: Dict[str, Any]) -> str:
        """Extract content from post, preferring markdown over HTML."""
        # Try enriched content first (from API)
        if enriched_post.get('content'):
            if enriched_post['content'].get('markdown'):
                return enriched_post['content']['markdown']
            elif enriched_post['content'].get('html'):
                return enriched_post['content']['html']
                
        # Fallback to original post content
        if original_post.get('contentMarkdown'):
            return original_post['contentMarkdown']
        elif original_post.get('content'):
            return original_post['content']
            
        return ""
        
    def _clean_content(self, content: str) -> str:
        """Clean and process content for 11ty."""
        if not content:
            return ""
            
        # Clean image URLs (remove HTML attributes)
        content = self._clean_image_urls(content)
        
        # Handle template conflicts (escape Nunjucks syntax)
        content = self._escape_template_syntax(content)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content
        
    def _clean_image_urls(self, content: str) -> str:
        """Remove HTML attributes from image URLs."""
        # Remove align and other attributes from image URLs
        # Example: ![](https://example.com/image.jpg align="center") -> ![](https://example.com/image.jpg)
        content = re.sub(r'(\!\[.*?\]\([^)]+?)\s+align="[^"]*"([^)]*\))', r'\1\2', content)
        content = re.sub(r'(\!\[.*?\]\([^)]+?)\s+width="[^"]*"([^)]*\))', r'\1\2', content)
        content = re.sub(r'(\!\[.*?\]\([^)]+?)\s+height="[^"]*"([^)]*\))', r'\1\2', content)
        
        return content
        
    def _escape_template_syntax(self, content: str) -> str:
        """Escape Nunjucks template syntax in content."""
        # Only wrap content in {% raw %} if it contains template syntax
        has_template_syntax = any([
            '{{' in content and '}}' in content,
            '{%' in content and '%}' in content,
            '{#' in content and '#}' in content
        ])
        
        if has_template_syntax:
            # Check if content already has raw tags
            if '{% raw %}' not in content:
                content = "{% raw %}\n" + content + "\n{% endraw %}"
                
        return content
        
    def _extract_metadata(self, original_post: Dict[str, Any], enriched_post: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize metadata from posts."""
        # Title and slug
        title = enriched_post.get('title') or original_post.get('title', 'Untitled')
        slug = enriched_post.get('slug') or original_post.get('slug', self._slugify(title))
        
        # Date
        date = self._parse_date(
            enriched_post.get('publishedAt') or 
            original_post.get('publishedAt') or 
            original_post.get('dateAdded')
        )
        
        # Excerpt
        excerpt = (
            enriched_post.get('brief') or 
            original_post.get('brief') or 
            self._generate_excerpt(title)
        )
        
        # Tags
        tags = self._extract_tags(enriched_post.get('tags', []))
        
        # Series
        series = self._extract_series(enriched_post.get('series'))
        
        # Cover image
        cover_image_url = None
        if enriched_post.get('coverImage', {}).get('url'):
            cover_image_url = enriched_post['coverImage']['url']
        elif original_post.get('coverImage'):
            cover_image_url = original_post['coverImage']
            
        # Read time
        read_time = (
            enriched_post.get('readTimeInMinutes') or 
            original_post.get('readTimeInMinutes', 5)
        )
        
        return {
            'title': title,
            'slug': slug,
            'date': date,
            'excerpt': excerpt,
            'tags': tags,
            'series': series,
            'cover_image_url': cover_image_url,
            'read_time': read_time
        }
        
    def _parse_date(self, date_string: Optional[str]) -> str:
        """Parse date string to YYYY-MM-DD format."""
        if not date_string:
            return datetime.date.today().strftime('%Y-%m-%d')
            
        try:
            # Handle ISO date strings
            if 'T' in date_string:
                date_part = date_string.split('T')[0]
                return date_part
            # Handle other date formats
            parsed_date = datetime.datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return datetime.date.today().strftime('%Y-%m-%d')
            
    def _extract_tags(self, tags_data: List[Dict[str, Any]]) -> List[str]:
        """Extract tag names from enriched tag data."""
        if not tags_data:
            return []
            
        tag_names = []
        for tag in tags_data:
            if isinstance(tag, dict):
                # From enriched data
                tag_name = tag.get('name', tag.get('id', ''))
            else:
                # From original data (just ID)
                tag_name = str(tag)
                
            if tag_name:
                tag_names.append(tag_name)
                
        return tag_names
        
    def _extract_series(self, series_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Extract series name from enriched series data."""
        if not series_data:
            return None
            
        if isinstance(series_data, dict):
            return series_data.get('name', series_data.get('id', ''))
        else:
            return str(series_data)
            
    def _generate_excerpt(self, title: str) -> str:
        """Generate a basic excerpt from title."""
        return f"Read about {title.lower()}"
        
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Convert to lowercase and replace spaces with hyphens
        slug = text.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[-\s]+', '-', slug)   # Replace spaces/multiple hyphens
        slug = slug.strip('-')                # Remove leading/trailing hyphens
        
        return slug
        
    def generate_markdown_file(self, post: Dict[str, Any]) -> str:
        """Generate complete markdown file content for a post."""
        try:
            template = self.jinja_env.get_template('post.md.j2')
            return template.render(post=post)
        except Exception as e:
            console.print(f"[red]Template error: {e}[/red]")
            # Fallback to manual generation
            return self._generate_manual_markdown(post)
            
    def _generate_manual_markdown(self, post: Dict[str, Any]) -> str:
        """Generate markdown manually if template fails."""
        frontmatter_lines = ['---']
        
        # Basic frontmatter
        frontmatter_lines.append(f'title: "{post["title"]}"')
        frontmatter_lines.append(f'date: {post["date"]}')
        frontmatter_lines.append(f'permalink: "{post["permalink"]}"')
        frontmatter_lines.append(f'layout: "{post["layout"]}"')
        
        if post.get('excerpt'):
            frontmatter_lines.append(f'excerpt: "{post["excerpt"]}"')
            
        if post.get('coverImage'):
            frontmatter_lines.append(f'coverImage: "{post["coverImage"]}"')
            
        if post.get('readTime'):
            frontmatter_lines.append(f'readTime: {post["readTime"]}')
            
        # Tags
        if post.get('tags'):
            tag_list = ', '.join([f'"{tag}"' for tag in post['tags']])
            frontmatter_lines.append(f'tags: [{tag_list}]')
            
        # Series
        if post.get('series'):
            frontmatter_lines.append(f'series: "{post["series"]}"')
            
        frontmatter_lines.append('---')
        frontmatter_lines.append('')
        
        # Content
        content = post.get('content', '')
        
        return '\n'.join(frontmatter_lines) + content
        
    def extract_images_from_content(self, content: str) -> List[str]:
        """Extract image URLs from markdown content."""
        if not content:
            return []
            
        # Match markdown image syntax: ![alt](url)
        image_pattern = r'!\[.*?\]\(([^)]+)\)'
        matches = re.findall(image_pattern, content)
        
        # Filter out relative URLs and data URLs
        image_urls = []
        for url in matches:
            url = url.strip()
            if url.startswith(('http://', 'https://')):
                image_urls.append(url)
                
        return image_urls