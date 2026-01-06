"""
Papers management routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import logging
from backend.storage import PaperRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("")
async def get_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    source: Optional[str] = None,
    min_score: Optional[float] = None
):
    """
    Get papers with pagination and filters
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of results per page
        search: Search query for title/abstract
        source: Filter by data source
        min_score: Minimum score filter
    """
    try:
        repo = PaperRepository()
        
        # This would need to be implemented in the repository
        # For now, return a stub
        papers = []
        total = 0
        
        return {
            "status": "success",
            "data": {
                "papers": papers,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }
    except Exception as e:
        logger.error(f"Failed to get papers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{paper_id}")
async def get_paper(paper_id: str):
    """Get a specific paper by ID"""
    try:
        repo = PaperRepository()
        # This would need to be implemented
        paper = None
        
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        return {"status": "success", "data": paper}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper {paper_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a paper"""
    try:
        repo = PaperRepository()
        # This would need to be implemented
        
        return {"status": "success", "message": "Paper deleted"}
    except Exception as e:
        logger.error(f"Failed to delete paper {paper_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
