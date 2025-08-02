"""
Advanced search utilities for optimized search functionality across the application.
Provides full-text search, filtering, and performance optimizations.
"""

from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.sql import Select
import re


class SearchConfig:
    """Configuration for search operations"""
    
    # Default search limits
    DEFAULT_LIMIT = 50
    MAX_LIMIT = 100
    
    # Search ranking weights
    EXACT_MATCH_WEIGHT = 10.0
    PREFIX_MATCH_WEIGHT = 5.0
    CONTAINS_MATCH_WEIGHT = 1.0
    
    # Full-text search configuration
    FTS_CONFIG = 'english'  # PostgreSQL full-text search configuration


class SearchQueryBuilder:
    """Advanced search query builder with optimization features"""
    
    def __init__(self, model: Type, session: AsyncSession):
        self.model = model
        self.session = session
        self.base_query = select(model)
        self.search_fields = []
        self.filters = []
        self.sort_fields = []
        
    def add_search_fields(self, *fields) -> 'SearchQueryBuilder':
        """Add fields to search in"""
        self.search_fields.extend(fields)
        return self
        
    def add_filter(self, condition) -> 'SearchQueryBuilder':
        """Add a filter condition"""
        self.filters.append(condition)
        return self
        
    def add_sort(self, field, direction='asc') -> 'SearchQueryBuilder':
        """Add sorting"""
        if direction.lower() == 'desc':
            self.sort_fields.append(field.desc())
        else:
            self.sort_fields.append(field.asc())
        return self
        
    def build_text_search(self, search_term: str, use_fts: bool = True):
        """Build optimized text search query"""
        if not search_term or not self.search_fields:
            query = self.base_query
        else:
            # Clean and prepare search term
            clean_term = self._clean_search_term(search_term)
            
            if use_fts and self._supports_fts():
                # Use PostgreSQL full-text search for better performance
                query = self._build_fts_query(clean_term)
            else:
                # Use ILIKE search for compatibility
                query = self._build_ilike_query(clean_term)
        
        # Apply filters
        if self.filters:
            query = query.where(and_(*self.filters))
            
        # Apply sorting
        if self.sort_fields:
            query = query.order_by(*self.sort_fields)
            
        return query
    
    def build_advanced_search(
        self, 
        search_term: str,
        exact_match_fields: List[str] = None,
        fuzzy_match_fields: List[str] = None,
        date_range: Dict[str, Any] = None,
        numeric_range: Dict[str, Any] = None
    ):
        """Build advanced search with multiple search strategies"""
        conditions = []
        
        if search_term and self.search_fields:
            clean_term = self._clean_search_term(search_term)
            
            # Exact match conditions (highest priority)
            if exact_match_fields:
                exact_conditions = [
                    field.ilike(clean_term) for field in exact_match_fields
                ]
                if exact_conditions:
                    conditions.append(or_(*exact_conditions))
            
            # Fuzzy match conditions
            if fuzzy_match_fields:
                fuzzy_conditions = [
                    field.ilike(f"%{clean_term}%") for field in fuzzy_match_fields
                ]
                if fuzzy_conditions:
                    conditions.append(or_(*fuzzy_conditions))
            
            # Default search in all fields
            if not exact_match_fields and not fuzzy_match_fields:
                search_conditions = [
                    field.ilike(f"%{clean_term}%") for field in self.search_fields
                ]
                if search_conditions:
                    conditions.append(or_(*search_conditions))
        
        # Date range filtering
        if date_range:
            for field_name, range_config in date_range.items():
                field = getattr(self.model, field_name, None)
                if field:
                    if 'start' in range_config:
                        conditions.append(field >= range_config['start'])
                    if 'end' in range_config:
                        conditions.append(field <= range_config['end'])
        
        # Numeric range filtering
        if numeric_range:
            for field_name, range_config in numeric_range.items():
                field = getattr(self.model, field_name, None)
                if field:
                    if 'min' in range_config:
                        conditions.append(field >= range_config['min'])
                    if 'max' in range_config:
                        conditions.append(field <= range_config['max'])
        
        # Build final query
        query = self.base_query
        if conditions:
            query = query.where(and_(*conditions))
            
        # Apply additional filters
        if self.filters:
            query = query.where(and_(*self.filters))
            
        # Apply sorting
        if self.sort_fields:
            query = query.order_by(*self.sort_fields)
            
        return query
    
    def _clean_search_term(self, term: str) -> str:
        """Clean and sanitize search term"""
        # Remove extra whitespace and special characters
        cleaned = re.sub(r'\s+', ' ', term.strip())
        # Escape special SQL characters
        cleaned = cleaned.replace('%', '\\%').replace('_', '\\_')
        return cleaned
    
    def _supports_fts(self) -> bool:
        """Check if the database supports full-text search"""
        # For now, assume PostgreSQL support
        return True
    
    def _build_fts_query(self, search_term: str):
        """Build full-text search query using PostgreSQL's capabilities"""
        # Create a tsvector from searchable fields
        search_vector_parts = []
        for field in self.search_fields:
            search_vector_parts.append(f"coalesce({field.key}, '')")
        
        search_vector = " || ' ' || ".join(search_vector_parts)
        
        # Build the full-text search query
        query = self.base_query.where(
            text(f"to_tsvector('{SearchConfig.FTS_CONFIG}', {search_vector}) @@ plainto_tsquery('{SearchConfig.FTS_CONFIG}', :search_term)")
        ).params(search_term=search_term)
        
        return query
    
    def _build_ilike_query(self, search_term: str):
        """Build ILIKE-based search query"""
        search_conditions = []
        
        for field in self.search_fields:
            # Exact match (highest weight)
            search_conditions.append(field.ilike(search_term))
            # Prefix match
            search_conditions.append(field.ilike(f"{search_term}%"))
            # Contains match
            search_conditions.append(field.ilike(f"%{search_term}%"))
        
        query = self.base_query.where(or_(*search_conditions))
        return query


class SearchResultProcessor:
    """Process and enhance search results"""
    
    @staticmethod
    def highlight_matches(text: str, search_term: str, highlight_tag: str = "mark") -> str:
        """Highlight search term matches in text"""
        if not text or not search_term:
            return text
            
        # Case-insensitive highlighting
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        highlighted = pattern.sub(
            f"<{highlight_tag}>\\g<0></{highlight_tag}>", 
            text
        )
        return highlighted
    
    @staticmethod
    def calculate_relevance_score(
        item: Any, 
        search_term: str, 
        search_fields: List[str]
    ) -> float:
        """Calculate relevance score for search results"""
        if not search_term:
            return 0.0
            
        score = 0.0
        search_term_lower = search_term.lower()
        
        for field_name in search_fields:
            field_value = getattr(item, field_name, None)
            if field_value:
                field_value_lower = str(field_value).lower()
                
                # Exact match
                if field_value_lower == search_term_lower:
                    score += SearchConfig.EXACT_MATCH_WEIGHT
                # Prefix match
                elif field_value_lower.startswith(search_term_lower):
                    score += SearchConfig.PREFIX_MATCH_WEIGHT
                # Contains match
                elif search_term_lower in field_value_lower:
                    score += SearchConfig.CONTAINS_MATCH_WEIGHT
                    
        return score
    
    @staticmethod
    def add_search_metadata(
        results: List[Any], 
        search_term: str, 
        search_fields: List[str],
        highlight: bool = False
    ) -> List[Dict[str, Any]]:
        """Add search metadata to results"""
        enhanced_results = []
        
        for item in results:
            result_dict = item.dict() if hasattr(item, 'dict') else item.__dict__
            
            # Add relevance score
            relevance_score = SearchResultProcessor.calculate_relevance_score(
                item, search_term, search_fields
            )
            result_dict['_search_score'] = relevance_score
            
            # Add highlighting if requested
            if highlight:
                for field_name in search_fields:
                    field_value = result_dict.get(field_name)
                    if field_value:
                        highlighted_value = SearchResultProcessor.highlight_matches(
                            str(field_value), search_term
                        )
                        result_dict[f'{field_name}_highlighted'] = highlighted_value
            
            enhanced_results.append(result_dict)
        
        # Sort by relevance score
        enhanced_results.sort(key=lambda x: x.get('_search_score', 0), reverse=True)
        
        return enhanced_results


# Convenience functions for common search patterns
async def quick_search(
    model: Type,
    search_fields: List[str],
    search_term: str,
    session: AsyncSession,
    limit: int = SearchConfig.DEFAULT_LIMIT,
    offset: int = 0
) -> List[Any]:
    """Quick search utility function"""
    builder = SearchQueryBuilder(model, session)
    builder.add_search_fields(*[getattr(model, field) for field in search_fields])
    
    query = builder.build_text_search(search_term)
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()


async def advanced_search(
    model: Type,
    search_config: Dict[str, Any],
    session: AsyncSession,
    limit: int = SearchConfig.DEFAULT_LIMIT,
    offset: int = 0
) -> List[Any]:
    """Advanced search utility function"""
    builder = SearchQueryBuilder(model, session)
    
    # Configure search fields
    if 'search_fields' in search_config:
        fields = [getattr(model, field) for field in search_config['search_fields']]
        builder.add_search_fields(*fields)
    
    # Configure filters
    if 'filters' in search_config:
        for filter_config in search_config['filters']:
            builder.add_filter(filter_config)
    
    # Configure sorting
    if 'sort' in search_config:
        for sort_config in search_config['sort']:
            field = getattr(model, sort_config['field'])
            direction = sort_config.get('direction', 'asc')
            builder.add_sort(field, direction)
    
    # Build and execute query
    query = builder.build_advanced_search(
        search_term=search_config.get('search_term', ''),
        exact_match_fields=search_config.get('exact_match_fields', []),
        fuzzy_match_fields=search_config.get('fuzzy_match_fields', []),
        date_range=search_config.get('date_range'),
        numeric_range=search_config.get('numeric_range')
    )
    
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()
