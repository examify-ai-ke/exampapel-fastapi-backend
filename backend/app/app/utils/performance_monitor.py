"""
Performance monitoring utility for database queries
"""

import time
import logging
from functools import wraps
from typing import Any, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

def monitor_query_performance(func: Callable) -> Callable:
    """
    Decorator to monitor query performance
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow queries (> 1 second)
            if execution_time > 1.0:
                logger.warning(
                    f"Slow query detected in {func.__name__}: {execution_time:.2f}s"
                )
            elif execution_time > 0.5:
                logger.info(
                    f"Query performance in {func.__name__}: {execution_time:.2f}s"
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Query failed in {func.__name__} after {execution_time:.2f}s: {str(e)}"
            )
            raise
    
    return wrapper

async def analyze_query_plan(db_session: AsyncSession, query_str: str) -> dict:
    """
    Analyze query execution plan for performance optimization
    """
    try:
        # Get query execution plan
        explain_query = text(f"EXPLAIN ANALYZE {query_str}")
        result = await db_session.execute(explain_query)
        plan = result.fetchall()
        
        return {
            "query": query_str,
            "execution_plan": [row[0] for row in plan],
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to analyze query plan: {str(e)}")
        return {"error": str(e)}

class QueryOptimizer:
    """
    Utility class for query optimization recommendations
    """
    
    @staticmethod
    def get_list_view_recommendations() -> dict:
        """
        Get recommendations for optimizing list view queries
        """
        return {
            "general_principles": [
                "Use load_only() to limit columns loaded",
                "Avoid deep relationship nesting in list views",
                "Load only essential fields for related entities",
                "Use selectinload for one-to-many relationships",
                "Use joinedload for many-to-one relationships with few records",
                "Consider using subqueryload for complex scenarios",
                "Implement proper database indexes",
                "Use pagination effectively"
            ],
            "list_view_patterns": {
                "basic_relationship": "selectinload(Model.relationship).load_only(RelatedModel.id, RelatedModel.name)",
                "user_info": "selectinload(Model.created_by).load_only(User.id, User.first_name, User.last_name, User.email)",
                "avoid_deep_nesting": "Don't use: selectinload(A.b).selectinload(B.c).selectinload(C.d)",
                "count_relationships": "Use len(model.relationships) in properties instead of loading full data"
            },
            "performance_targets": {
                "list_queries": "< 500ms",
                "detail_queries": "< 1000ms",
                "search_queries": "< 2000ms"
            }
        }
    
    @staticmethod
    def optimize_selectinload_chain(relationships: list) -> str:
        """
        Generate optimized selectinload chain
        """
        if len(relationships) == 1:
            return f"selectinload({relationships[0]})"
        
        # For multiple relationships, suggest loading only essential fields
        optimized = []
        for rel in relationships:
            if "." in rel:
                # Deep relationship - suggest load_only
                parts = rel.split(".")
                base = ".".join(parts[:-1])
                field = parts[-1]
                optimized.append(f"selectinload({base}).load_only({field}.id, {field}.name)")
            else:
                optimized.append(f"selectinload({rel})")
        
        return ", ".join(optimized)
