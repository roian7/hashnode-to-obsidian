"""
Obsidian transformer module.

Converts Hashnode post data to Obsidian-compatible markdown format with proper frontmatter.
"""

import re
import datetime
from typing import Dict, List, Any, Optional
from rich.console import Console

console = Console()

# Compile regex patterns once at module level for better performance
RAW_BLOCK_START = re.compile(r'{% raw %}\s*')
RAW_BLOCK_END = re.compile(r'\s*{% endraw %}')
IMAGE_ALIGN_PATTERN = re.compile(r'(\!\[.*?\]\([^)]+?)\s+align="[^"]*"([^)]*\))')
IMAGE_WIDTH_PATTERN = re.compile(r'(\!\[.*?\]\([^)]+?)\s+width="[^"]*"([^)]*\))')
IMAGE_HEIGHT_PATTERN = re.compile(r'(\!\[.*?\]\([^)]+?)\s+height="[^"]*"([^)]*\))')
IMAGE_URL_PATTERN = re.compile(r'!\[.*?\]\(([^)]+)\)')
SLUG_SPECIAL_CHARS = re.compile(r'[^\w\s-]')
SLUG_SPACES = re.compile(r'[-\s]+')
TAG_QUOTES = re.compile(r'["\']')
TAG_SPECIAL_CHARS = re.compile(r'[^\w\-_]')
EXTRA_WHITESPACE = re.compile(r'\n\s*\n\s*\n')


class ObsidianTransformer:
    """Transforms Hashnode content to Obsidian format."""
    
    def __init__(self):
        """Initialize transformer."""
        self.formatter = ObsidianFormatter()
        
    def transform_post(self, original_post: Dict[str, Any], enriched_post: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single post to Obsidian format."""
        # Extract content - prefer contentMarkdown, fallback to content
        content = self._get_post_content(original_post, enriched_post)
        
        # Clean and process the content for Obsidian
        cleaned_content = self._clean_content_for_obsidian(content)
        
        # Extract and process metadata
        metadata = self._extract_metadata(original_post, enriched_post)
        
        # Create transformed post object for Obsidian
        transformed_post = {
            'title': metadata['title'],
            'subtitle': metadata['subtitle'],
            'slug': metadata['slug'],
            'description': metadata['description'],  # Changed from excerpt
            'date': metadata['date'],
            'updated': metadata['updated'],
            'status': metadata['status'],
            'tags': metadata['tags'],
            'series': metadata['series'],
            'reading_time': metadata['reading_time'],
            'cover_image': metadata['cover_image_url'],
            'content': cleaned_content
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
        
    def _clean_content_for_obsidian(self, content: str) -> str:
        """Clean and process content for Obsidian (remove 11ty-specific formatting)."""
        if not content:
            return ""
            
        # Remove {% raw %} blocks (11ty-specific)
        content = self._remove_raw_blocks(content)
        
        # Remove Nunjucks template escaping
        content = self._remove_template_escaping(content)
        
        # Clean image URLs (remove HTML attributes)
        content = self._clean_image_urls(content)
        
        # Clean up extra whitespace
        content = EXTRA_WHITESPACE.sub('\n\n', content)
        content = content.strip()
        
        return content
        
    def _remove_raw_blocks(self, content: str) -> str:
        """Remove {% raw %} and {% endraw %} blocks."""
        # Remove raw block wrappers
        content = RAW_BLOCK_START.sub('', content)
        content = RAW_BLOCK_END.sub('', content)
        return content
        
    def _remove_template_escaping(self, content: str) -> str:
        """Remove Nunjucks template syntax escaping."""
        # Since we removed raw blocks, we don't need additional escaping for Obsidian
        # This is a placeholder for any other template-specific cleanup
        return content
        
    def _clean_image_urls(self, content: str) -> str:
        """Remove HTML attributes from image URLs."""
        # Remove align and other attributes from image URLs
        # Example: ![](https://example.com/image.jpg align="center") -> ![](https://example.com/image.jpg)
        content = IMAGE_ALIGN_PATTERN.sub(r'\1\2', content)
        content = IMAGE_WIDTH_PATTERN.sub(r'\1\2', content)
        content = IMAGE_HEIGHT_PATTERN.sub(r'\1\2', content)
        
        return content
        
    def _extract_metadata(self, original_post: Dict[str, Any], enriched_post: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and normalize metadata from posts for Obsidian format."""
        # Title and slug
        title = enriched_post.get('title') or original_post.get('title', 'Untitled')
        slug = enriched_post.get('slug') or original_post.get('slug', self._slugify(title))
        
        # Subtitle (from original post)
        subtitle = original_post.get('subtitle', '')
        
        # Date and updated
        date = self._parse_date(
            enriched_post.get('publishedAt') or 
            original_post.get('publishedAt') or 
            original_post.get('dateAdded')
        )
        
        updated = self._parse_date(original_post.get('updatedAt'))
        
        # Description (changed from excerpt to match SEO standards)
        description = (
            enriched_post.get('brief') or 
            original_post.get('brief') or 
            self._generate_description(title)
        )
        
        # Status (determine if draft or published)
        status = ['published'] if original_post.get('isActive', True) else ['draft']
        
        # Tags (format for Obsidian)
        tags = self.formatter.format_tags(enriched_post.get('tags', []))
        
        # Series (simple text field)
        series = self.formatter.format_series(enriched_post.get('series'))
        
        # Cover image (keep URL for now)
        cover_image_url = None
        if enriched_post.get('coverImage', {}).get('url'):
            cover_image_url = enriched_post['coverImage']['url']
        elif original_post.get('coverImage'):
            cover_image_url = original_post['coverImage']
            
        # Reading time
        reading_time = (
            enriched_post.get('readTimeInMinutes') or 
            original_post.get('readTime') or
            original_post.get('readTimeInMinutes', 5)
        )
        
        return {
            'title': title,
            'subtitle': subtitle,
            'slug': slug,
            'description': description,
            'date': date,
            'updated': updated,
            'status': status,
            'tags': tags,
            'series': series,
            'cover_image_url': cover_image_url,
            'reading_time': reading_time
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
            
    def _generate_description(self, title: str) -> str:
        """Generate a basic description from title."""
        return f"Read about {title.lower()}"
        
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Convert to lowercase and replace spaces with hyphens
        slug = text.lower()
        slug = SLUG_SPECIAL_CHARS.sub('', slug)  # Remove special chars
        slug = SLUG_SPACES.sub('-', slug)   # Replace spaces/multiple hyphens
        slug = slug.strip('-')                # Remove leading/trailing hyphens
        
        return slug
        
    def generate_obsidian_markdown(self, post: Dict[str, Any]) -> str:
        """Generate complete Obsidian markdown file content for a post."""
        return self.formatter.generate_frontmatter_and_content(post)


class ObsidianFormatter:
    """Handles Obsidian-specific formatting."""
    
    def format_tags(self, tags_data: List[Dict[str, Any]]) -> List[str]:
        """Format tags for Obsidian (replace spaces with underscores, clean special chars)."""
        if not tags_data:
            return []
            
        formatted_tags = []
        for tag in tags_data:
            if isinstance(tag, dict):
                # From enriched data
                tag_name = tag.get('name', tag.get('id', ''))
            else:
                # From original data (just ID)
                tag_name = str(tag)
                
            if tag_name:
                # Format tag for Obsidian: replace spaces with underscores, remove special chars
                clean_tag = self._clean_tag_name(tag_name)
                if clean_tag:
                    formatted_tags.append(clean_tag)
                
        return formatted_tags
        
    def _clean_tag_name(self, tag_name: str) -> str:
        """Clean tag name for Obsidian format."""
        # Replace spaces with underscores
        clean_name = tag_name.replace(' ', '_')
        
        # Remove quotes and problematic characters
        clean_name = TAG_QUOTES.sub('', clean_name)
        
        # Remove other special characters except underscores and hyphens
        clean_name = TAG_SPECIAL_CHARS.sub('', clean_name)
        
        # Handle special cases like "Next.js" -> "Next_js"
        clean_name = clean_name.replace('.', '_')
        
        return clean_name
        
    def format_series(self, series_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """Format series as simple text field for Obsidian."""
        if not series_data:
            return None
            
        if isinstance(series_data, dict):
            return series_data.get('name', series_data.get('id', ''))
        else:
            return str(series_data)
            
    def generate_frontmatter_and_content(self, post: Dict[str, Any]) -> str:
        """Generate complete markdown file with Obsidian YAML frontmatter."""
        frontmatter_lines = ['---']
        
        # Required fields
        frontmatter_lines.append(f'title: "{post["title"]}"')
        
        # Optional fields
        if post.get('subtitle'):
            frontmatter_lines.append(f'subtitle: "{post["subtitle"]}"')
            
        if post.get('slug'):
            frontmatter_lines.append(f'slug: "{post["slug"]}"')
            
        if post.get('description'):
            description_yaml = self._format_description_yaml(post['description'])
            frontmatter_lines.append(f'description: {description_yaml}')
            
        if post.get('date'):
            frontmatter_lines.append(f'date: {post["date"]}')
            
        if post.get('updated'):
            frontmatter_lines.append(f'updated: {post["updated"]}')
            
        # Status
        if post.get('status'):
            frontmatter_lines.append('status:')
            for status in post['status']:
                frontmatter_lines.append(f'  - {status}')
                
        # Tags
        if post.get('tags'):
            frontmatter_lines.append('tags:')
            for tag in post['tags']:
                frontmatter_lines.append(f'  - {tag}')
                
        # Series
        if post.get('series'):
            frontmatter_lines.append(f'series: "{post["series"]}"')
            
        # Reading time
        if post.get('reading_time'):
            frontmatter_lines.append(f'reading_time: {post["reading_time"]}')
            
        # Cover image
        if post.get('cover_image'):
            frontmatter_lines.append(f'cover_image: "{post["cover_image"]}"')
            
        frontmatter_lines.append('---')
        frontmatter_lines.append('')
        
        # Content
        content = post.get('content', '')
        
        return '\n'.join(frontmatter_lines) + content
        
    def _format_description_yaml(self, description: str) -> str:
        """Format description using YAML literal block scalar for multiline content."""
        if not description:
            return '""'
            
        # Clean the description first
        clean_description = description.strip()
        
        # Check if we need multiline format
        has_newlines = '\n' in clean_description
        is_long = len(clean_description) > 80
        has_special_chars = any(char in clean_description for char in ['"', "'", ':', '#'])
        
        if has_newlines or is_long or has_special_chars:
            # Use literal block scalar (|) for multiline/complex content
            lines = clean_description.split('\n')
            yaml_lines = ['|']
            for line in lines:
                # Indent each line with 2 spaces
                yaml_lines.append(f'  {line}')
            return '\n'.join(yaml_lines)
        else:
            # Use quoted string for simple descriptions
            # Escape quotes in the description
            escaped = clean_description.replace('"', '\\"')
            return f'"{escaped}"'
            
    def extract_images_from_content(self, content: str) -> List[str]:
        """Extract image URLs from markdown content."""
        if not content:
            return []
            
        # Match markdown image syntax: ![alt](url)
        matches = IMAGE_URL_PATTERN.findall(content)
        
        # Filter out relative URLs and data URLs
        image_urls = []
        for url in matches:
            url = url.strip()
            if url.startswith(('http://', 'https://')):
                image_urls.append(url)
                
        return image_urls