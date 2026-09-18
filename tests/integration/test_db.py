"""Integration tests for database operations."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from local_llm_benchmark.db import Base, get_db
from local_llm_benchmark.schemas.response import Result


class TestDatabaseConnection:
    """Integration tests for database connectivity."""
    
    @pytest.fixture
def test_engine(tmp_path):
        """Create a test SQLite engine."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(engine)
        yield engine
        Base.metadata.drop_all(engine)
    
    @pytest.fixture
def test_session(self, test_engine):
        """Create a test session."""
        SessionLocal = sessionmaker(bind=test_engine)
        session = SessionLocal()
        yield session
        session.close()
    
    def test_engine_creation(self, test_engine):
        """Test database engine creation."""
        assert test_engine is not None
        assert test_engine.url
    
    def test_session_creation(self, test_session):
        """Test session creation."""
        assert test_session is not None
    
    def test_query_count(self, test_session):
        """Test counting rows in database."""
        count = test_session.execute(text("SELECT COUNT(*) FROM results")).scalar()
        assert count == 0  # Empty database
    
    def test_insert_result(self, test_session):
        """Test inserting a result into database."""
        result = Result(
            id="test-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            input="Test input",
            output="Test output",
            quality_score=0.92,
            safety_score=0.98,
            accuracy_score=0.89
        )
        
        test_session.add(result)
        test_session.commit()
        
        # Verify insertion
        count = test_session.execute(text("SELECT COUNT(*) FROM results")).scalar()
        assert count == 1
    
    def test_select_results(self, test_session):
        """Test selecting results from database."""
        # Insert test data
        result1 = Result(
            id="result-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92
        )
        result2 = Result(
            id="result-2",
            challenge_id="challenge-1",
            engine_id="engine-2",
            task_id="task-1",
            quality_score=0.85
        )
        
        test_session.add(result1)
        test_session.add(result2)
        test_session.commit()
        
        # Select all results
        results = test_session.execute(text("SELECT * FROM results")).fetchall()
        assert len(results) == 2
        
        # Select by challenge
        challenge_results = test_session.execute(
            text("SELECT * FROM results WHERE challenge_id = :challenge_id")
        ).fetchall()
        assert len(challenge_results) == 2
        
        # Clean up
        test_session.execute(text("DELETE FROM results"))
        test_session.commit()


class TestDatabaseQueries:
    """Integration tests for database queries."""
    
    @pytest.fixture
def test_db_session(self, tmp_path):
        """Create a test database session."""
        db_path = tmp_path / "benchmark.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()
    
    def test_count_results(self, test_db_session):
        """Test counting results."""
        # Insert test data
        for i in range(100):
            result = Result(
                id=f"result-{i}",
                challenge_id="challenge-1",
                engine_id="engine-1",
                task_id="task-1",
                quality_score=0.5 + (i % 100) / 100.0
            )
            test_db_session.add(result)
        test_db_session.commit()
        
        # Count results
        count = test_db_session.execute(text("SELECT COUNT(*) FROM results")).scalar()
        assert count == 100
    
    def test_average_quality_score(self, test_db_session):
        """Test calculating average quality score."""
        # Insert test data with known average
        for i in range(10):
            result = Result(
                id=f"result-{i}",
                challenge_id="challenge-1",
                engine_id="engine-1",
                task_id="task-1",
                quality_score=0.9 + (i % 5) / 10.0  # Average = 0.95
            )
            test_db_session.add(result)
        test_db_session.commit()
        
        # Calculate average
        avg = test_db_session.execute(
            text("SELECT AVG(quality_score) FROM results")
        ).scalar()
        assert avg == pytest.approx(0.95)
    
    def test_filter_by_engine(self, test_db_session):
        """Test filtering results by engine."""
        # Insert test data for multiple engines
        for engine_id in ["engine-1", "engine-2", "engine-3"]:
            for i in range(50):
                result = Result(
                    id=f"result-{i}",
                    challenge_id="challenge-1",
                    engine_id=engine_id,
                    task_id="task-1",
                    quality_score=0.5 + (i % 100) / 100.0
                )
                test_db_session.add(result)
        test_db_session.commit()
        
        # Filter by engine
        engine1_results = test_db_session.execute(
            text("SELECT COUNT(*) FROM results WHERE engine_id = 'engine-1'")
        ).scalar()
        assert engine1_results == 50
    
    def test_filter_by_quality_threshold(self, test_db_session):
        """Test filtering results by quality threshold."""
        # Insert test data with different quality scores
        for score in [0.5, 0.6, 0.7, 0.8, 0.9]:
            for _ in range(100):
                result = Result(
                    id="result",
                    challenge_id="challenge-1",
                    engine_id="engine-1",
                    task_id="task-1",
                    quality_score=score
                )
                test_db_session.add(result)
        test_db_session.commit()
        
        # Count results above threshold
        high_quality = test_db_session.execute(
            text("SELECT COUNT(*) FROM results WHERE quality_score > 0.75")
        ).scalar()
        assert high_quality == 200  # 0.8, 0.9 scores
    
    def test_order_by_quality(self, test_db_session):
        """Test ordering results by quality."""
        # Insert test data
        for i in range(5):
            result = Result(
                id=f"result-{i}",
                challenge_id="challenge-1",
                engine_id="engine-1",
                task_id="task-1",
                quality_score=0.5 + i * 0.1  # 0.5, 0.6, 0.7, 0.8, 0.9
            )
            test_db_session.add(result)
        test_db_session.commit()
        
        # Order by quality descending
        results = test_db_session.execute(
            text("SELECT quality_score FROM results ORDER BY quality_score DESC")
        ).fetchall()
        assert [r.quality_score for r in results] == [0.9, 0.8, 0.7, 0.6, 0.5]


class TestDatabaseCleanup:
    """Integration tests for database cleanup."""
    
    def test_delete_all_results(self, test_db_session):
        """Test deleting all results."""
        # Insert test data
        result = Result(
            id="test-1",
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92
        )
        test_db_session.add(result)
        test_db_session.commit()
        
        # Verify insertion
        count = test_db_session.execute(text("SELECT COUNT(*) FROM results")).scalar()
        assert count == 1
        
        # Delete all
        test_db_session.execute(text("DELETE FROM results"))
        test_db_session.commit()
        
        # Verify deletion
        count = test_db_session.execute(text("SELECT COUNT(*) FROM results")).scalar()
        assert count == 0
    
    def test_transaction_rollback(self, test_db_session):
        """Test transaction rollback on error."""
        try:
            # Insert in transaction
            result = Result(
                id="test-1",
                challenge_id="challenge-1",
                engine_id="engine-1",
                task_id="task-1",
                quality_score=0.92
            )
            test_db_session.add(result)
            test_db_session.commit()  # Commit to see if rollback happens
            
            # Trigger rollback
            raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify rollback
        count = test_db_session.execute(text("SELECT COUNT(*) FROM results")).scalar()
        assert count == 0
