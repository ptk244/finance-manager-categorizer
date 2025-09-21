"""
Session manager for handling user sessions and state management
"""
import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from app.models.transaction import Transaction, CategorizedTransaction
from app.models.insights import FinancialInsights

logger = structlog.get_logger(__name__)


class SessionManager:
    """
    Manages user sessions and maintains state across requests.
    In a production environment, this would integrate with a database or cache.
    """
    
    def __init__(self):
        self.logger = logger.bind(service="SessionManager")
        
        # In-memory session storage (for demo purposes)
        # In production, this would be Redis, database, or similar
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._default_session_id = "default"
        
        self.logger.info("Session manager initialized")
    
    def get_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session data
        
        Args:
            session_id: Session identifier (uses default if None)
            
        Returns:
            Session data dictionary
        """
        if session_id is None:
            session_id = self._default_session_id
        
        if session_id not in self._sessions:
            self._sessions[session_id] = self._create_new_session()
        
        return self._sessions[session_id]
    
    def update_session(self, 
                      session_id: Optional[str] = None, 
                      **updates) -> Dict[str, Any]:
        """
        Update session data
        
        Args:
            session_id: Session identifier
            **updates: Key-value pairs to update
            
        Returns:
            Updated session data
        """
        if session_id is None:
            session_id = self._default_session_id
        
        session = self.get_session(session_id)
        session.update(updates)
        session["last_updated"] = datetime.now().isoformat()
        
        self.logger.debug("Session updated", 
                         session_id=session_id, 
                         updates=list(updates.keys()))
        
        return session
    
    def reset_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Reset session to initial state
        
        Args:
            session_id: Session identifier
            
        Returns:
            New session data
        """
        if session_id is None:
            session_id = self._default_session_id
        
        self._sessions[session_id] = self._create_new_session()
        
        self.logger.info("Session reset", session_id=session_id)
        
        return self._sessions[session_id]
    
    def delete_session(self, session_id: str):
        """
        Delete a session
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            self.logger.info("Session deleted", session_id=session_id)
    
    def _create_new_session(self) -> Dict[str, Any]:
        """Create a new session with default values"""
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "transactions": [],
            "categorized_transactions": [],
            "category_summary": {},
            "insights": None,
            "file_info": None,
            "processing_history": [],
            "user_corrections": [],
            "session_stats": {
                "files_processed": 0,
                "transactions_categorized": 0,
                "insights_generated": 0,
                "corrections_made": 0
            }
        }
    
    def store_transactions(self, 
                          transactions: list, 
                          file_info: Dict[str, Any],
                          session_id: Optional[str] = None):
        """
        Store transactions in session
        
        Args:
            transactions: List of transactions
            file_info: File processing information
            session_id: Session identifier
        """
        session = self.get_session(session_id)
        
        session["transactions"] = [t.dict() if hasattr(t, 'dict') else t for t in transactions]
        session["file_info"] = file_info
        session["last_upload"] = datetime.now().isoformat()
        session["session_stats"]["files_processed"] += 1
        
        # Add to processing history
        session["processing_history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "file_upload",
            "details": {
                "filename": file_info.get("filename"),
                "transaction_count": len(transactions),
                "file_type": file_info.get("file_type")
            }
        })
        
        self.update_session(session_id, **session)
        
        self.logger.info("Transactions stored in session", 
                        session_id=session_id or self._default_session_id,
                        transaction_count=len(transactions))
    
    def store_categorized_transactions(self, 
                                     categorized_transactions: list,
                                     category_summary: Dict[str, Any],
                                     session_id: Optional[str] = None):
        """
        Store categorized transactions in session
        
        Args:
            categorized_transactions: List of categorized transactions
            category_summary: Category summary data
            session_id: Session identifier
        """
        session = self.get_session(session_id)
        
        session["categorized_transactions"] = [
            t.dict() if hasattr(t, 'dict') else t for t in categorized_transactions
        ]
        session["category_summary"] = category_summary
        session["last_categorization"] = datetime.now().isoformat()
        session["session_stats"]["transactions_categorized"] = len(categorized_transactions)
        
        # Add to processing history
        session["processing_history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "categorization",
            "details": {
                "transaction_count": len(categorized_transactions),
                "categories_found": len(category_summary),
                "total_amount": sum(
                    summary.get("total_amount", 0) 
                    for summary in category_summary.values()
                )
            }
        })
        
        self.update_session(session_id, **session)
        
        self.logger.info("Categorized transactions stored in session", 
                        session_id=session_id or self._default_session_id,
                        transaction_count=len(categorized_transactions))
    
    def store_insights(self, 
                      insights: FinancialInsights,
                      session_id: Optional[str] = None):
        """
        Store financial insights in session
        
        Args:
            insights: Financial insights object
            session_id: Session identifier
        """
        session = self.get_session(session_id)
        
        session["insights"] = insights.dict() if hasattr(insights, 'dict') else insights
        session["last_insights"] = datetime.now().isoformat()
        session["session_stats"]["insights_generated"] += 1
        
        # Add to processing history
        session["processing_history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "insights_generation",
            "details": {
                "key_insights_count": len(insights.key_insights if hasattr(insights, 'key_insights') else []),
                "recommendations_count": len(insights.recommendations if hasattr(insights, 'recommendations') else [])
            }
        })
        
        self.update_session(session_id, **session)
        
        self.logger.info("Insights stored in session", 
                        session_id=session_id or self._default_session_id)
    
    def record_user_correction(self, 
                              transaction_index: int,
                              original_category: str,
                              correct_category: str,
                              correct_subcategory: Optional[str] = None,
                              session_id: Optional[str] = None):
        """
        Record user correction for learning purposes
        
        Args:
            transaction_index: Index of corrected transaction
            original_category: Original AI-assigned category
            correct_category: User-provided correct category
            correct_subcategory: User-provided subcategory
            session_id: Session identifier
        """
        session = self.get_session(session_id)
        
        correction = {
            "timestamp": datetime.now().isoformat(),
            "transaction_index": transaction_index,
            "original_category": original_category,
            "correct_category": correct_category,
            "correct_subcategory": correct_subcategory
        }
        
        session["user_corrections"].append(correction)
        session["session_stats"]["corrections_made"] += 1
        
        # Add to processing history
        session["processing_history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "user_correction",
            "details": correction
        })
        
        self.update_session(session_id, **session)
        
        self.logger.info("User correction recorded", 
                        session_id=session_id or self._default_session_id,
                        transaction_index=transaction_index,
                        original_category=original_category,
                        correct_category=correct_category)
    
    def get_session_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive session status
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status information
        """
        session = self.get_session(session_id)
        
        transactions = session.get("transactions", [])
        categorized_transactions = session.get("categorized_transactions", [])
        insights = session.get("insights")
        
        return {
            "session_id": session_id or self._default_session_id,
            "has_transactions": len(transactions) > 0,
            "has_categorized_data": len(categorized_transactions) > 0,
            "has_insights": insights is not None,
            "transaction_count": len(transactions),
            "categorized_count": len(categorized_transactions),
            "categories_count": len(session.get("category_summary", {})),
            "ready_for_categorization": len(transactions) > 0,
            "ready_for_insights": len(categorized_transactions) > 0,
            "last_upload_time": session.get("last_upload"),
            "last_categorization_time": session.get("last_categorization"),
            "last_insights_time": session.get("last_insights"),
            "session_stats": session.get("session_stats", {}),
            "created_at": session.get("created_at"),
            "last_updated": session.get("last_updated")
        }
    
    def get_processing_history(self, session_id: Optional[str] = None) -> list:
        """
        Get session processing history
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of processing events
        """
        session = self.get_session(session_id)
        return session.get("processing_history", [])
    
    def get_user_corrections(self, session_id: Optional[str] = None) -> list:
        """
        Get user corrections history
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of user corrections
        """
        session = self.get_session(session_id)
        return session.get("user_corrections", [])
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up old sessions
        
        Args:
            max_age_hours: Maximum age of sessions to keep
        """
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        sessions_to_delete = []
        
        for session_id, session_data in self._sessions.items():
            if session_id == self._default_session_id:
                continue  # Don't delete default session
            
            created_at_str = session_data.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_time:
                        sessions_to_delete.append(session_id)
                except ValueError:
                    # Invalid timestamp, mark for deletion
                    sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
        
        if sessions_to_delete:
            self.logger.info("Cleaned up old sessions", 
                           deleted_count=len(sessions_to_delete))
    
    def export_session_data(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export session data for backup or analysis
        
        Args:
            session_id: Session identifier
            
        Returns:
            Complete session data
        """
        session = self.get_session(session_id)
        
        return {
            "session_id": session_id or self._default_session_id,
            "export_timestamp": datetime.now().isoformat(),
            "session_data": session.copy()
        }
    
    def import_session_data(self, 
                           session_data: Dict[str, Any], 
                           session_id: Optional[str] = None):
        """
        Import session data from backup
        
        Args:
            session_data: Session data to import
            session_id: Target session identifier
        """
        if session_id is None:
            session_id = self._default_session_id
        
        # Validate session data structure
        required_fields = ["transactions", "categorized_transactions", "session_stats"]
        if not all(field in session_data for field in required_fields):
            raise ValueError("Invalid session data format")
        
        self._sessions[session_id] = session_data
        
        self.logger.info("Session data imported", 
                        session_id=session_id,
                        transaction_count=len(session_data.get("transactions", [])))
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of all sessions
        
        Returns:
            Summary of session manager state
        """
        total_sessions = len(self._sessions)
        total_transactions = sum(
            len(session.get("transactions", [])) 
            for session in self._sessions.values()
        )
        total_categorized = sum(
            len(session.get("categorized_transactions", []))
            for session in self._sessions.values()
        )
        
        return {
            "total_sessions": total_sessions,
            "total_transactions_processed": total_transactions,
            "total_transactions_categorized": total_categorized,
            "active_session_ids": list(self._sessions.keys()),
            "default_session_id": self._default_session_id,
            "session_manager_stats": {
                "memory_usage_mb": self._estimate_memory_usage(),
                "oldest_session": self._get_oldest_session_time(),
                "newest_session": self._get_newest_session_time()
            }
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB (rough approximation)"""
        import sys
        
        total_size = 0
        for session in self._sessions.values():
            total_size += sys.getsizeof(str(session))
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _get_oldest_session_time(self) -> Optional[str]:
        """Get timestamp of oldest session"""
        oldest_time = None
        
        for session in self._sessions.values():
            created_at = session.get("created_at")
            if created_at and (oldest_time is None or created_at < oldest_time):
                oldest_time = created_at
        
        return oldest_time
    
    def _get_newest_session_time(self) -> Optional[str]:
        """Get timestamp of newest session"""
        newest_time = None
        
        for session in self._sessions.values():
            created_at = session.get("created_at")
            if created_at and (newest_time is None or created_at > newest_time):
                newest_time = created_at
        
        return newest_time