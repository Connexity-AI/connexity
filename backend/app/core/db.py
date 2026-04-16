from sqlalchemy import text
from sqlmodel import Session, SQLModel, col, create_engine, select

from app import crud
from app.core.config import settings
from app.models import (
    AgentCreate,
    Difficulty,
    EvalSetCreate,
    EvalSetMemberEntry,
    ExpectedToolCall,
    RunCreate,
    RunStatus,
    RunUpdate,
    TestCaseCreate,
    TestCaseResultCreate,
    TestCaseResultUpdate,
    TestCaseStatus,
    User,
    UserCreate,
)

if not settings.SQLALCHEMY_DATABASE_URI:
    raise RuntimeError("DATABASE_URL or POSTGRES_* env vars must be configured")
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    # Wipe everything
    truncate_all_tables(session)

    # Seed one superuser
    # Credentials come from .env — defaults: admin@example.com / password
    user_in = UserCreate(
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        is_superuser=True,
        full_name="Admin",
    )
    crud.create_user(session=session, user_create=user_in)

    # Seed eval-domain entities
    _seed_eval_data(session)

    session.commit()


def _seed_eval_data(session: Session) -> None:
    """Seed eval-domain entities for dev/testing."""
    admin = session.exec(select(User).where(col(User.is_superuser).is_(True))).first()
    owner_id = admin.id if admin else None

    # Agents
    agent_cs = crud.create_agent(
        session=session,
        agent_in=AgentCreate(
            name="Customer Support Bot",
            description="Handles billing inquiries and account issues",
            endpoint_url="http://localhost:8081/agent",
            agent_metadata={"model": "claude-3-5-sonnet", "version": "1.0"},
        ),
        created_by=owner_id,
    )
    agent_sales = crud.create_agent(
        session=session,
        agent_in=AgentCreate(
            name="Sales Assistant",
            description="Qualifies leads and answers product questions",
            endpoint_url="http://localhost:8082/agent",
            agent_metadata={"model": "gpt-4o", "version": "2.1"},
        ),
        created_by=owner_id,
    )

    # Test cases
    s_refund = crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(
            name="Refund Request — Valid",
            description="Customer requests refund within 30-day window",
            difficulty=Difficulty.NORMAL,
            tags=["billing", "refund", "happy-path"],
            status=TestCaseStatus.ACTIVE,
            persona_context=(
                "[Persona type]\npolite-customer\n\n"
                "[Description]\nPolite customer who purchased 5 days ago\n\n"
                "[Behavioral instructions]\n"
                "Be cooperative but insistent on getting a full refund. "
                "Provide order number when asked."
            ),
            first_message="Hi, I'd like to request a refund for my recent order.",
            user_context={
                "order_id": "ORD-12345",
                "purchase_date": "2026-03-15",
                "amount": 49.99,
            },
            expected_outcomes=[
                "Agent MUST initiate refund for the customer",
                "Customer MUST be satisfied with the resolution",
            ],
            expected_tool_calls=[
                ExpectedToolCall(
                    tool="lookup_order", expected_params={"order_id": "ORD-12345"}
                ),
            ],
        ),
    )
    s_escalation = crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(
            name="Angry Escalation",
            description="Customer is frustrated after multiple failed attempts",
            difficulty=Difficulty.HARD,
            tags=["billing", "escalation", "edge-case"],
            status=TestCaseStatus.ACTIVE,
            persona_context=(
                "[Persona type]\nfrustrated-customer\n\n"
                "[Description]\nFrustrated customer with 3 prior contacts, increasingly angry\n\n"
                "[Behavioral instructions]\n"
                "Express frustration. Demand to speak to a supervisor. "
                "If not transferred within 3 turns, threaten to cancel account."
            ),
            first_message="I've called three times already and nobody has fixed my issue!",
            user_context={
                "account_id": "ACC-67890",
                "prior_contacts": 3,
                "issue": "billing overcharge",
            },
            expected_outcomes=[
                "Agent MUST escalate to a supervisor",
                "Agent MUST offer compensation for the inconvenience",
            ],
        ),
    )
    s_product = crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(
            name="Product Comparison",
            description="Customer asks for a comparison between two products",
            difficulty=Difficulty.NORMAL,
            tags=["sales", "product-info"],
            status=TestCaseStatus.ACTIVE,
            persona_context=(
                "[Persona type]\nbudget-shopper\n\n"
                "[Description]\nBudget-conscious shopper comparing two subscription plans\n\n"
                "[Behavioral instructions]\n"
                "Ask detailed questions about pricing, features, and limitations. "
                "Push back on upselling."
            ),
            first_message="Can you help me compare Plan A and Plan B?",
            user_context={"budget": 50, "team_size": 5},
            expected_outcomes=[
                "Agent MUST provide a comparison of the two plans",
                "Agent MUST give a recommendation based on the customer's needs",
            ],
        ),
    )
    crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(
            name="Draft Test Case — WIP",
            description="Not yet ready for evaluation",
            difficulty=Difficulty.NORMAL,
            tags=["draft"],
            status=TestCaseStatus.DRAFT,
        ),
    )
    crud.create_test_case(
        session=session,
        test_case_in=TestCaseCreate(
            name="Archived Legacy Test Case",
            description="Deprecated test case from v0",
            difficulty=Difficulty.HARD,
            tags=["legacy", "archived"],
            status=TestCaseStatus.ARCHIVED,
        ),
    )

    # Eval sets
    billing_set = crud.create_eval_set(
        session=session,
        eval_set_in=EvalSetCreate(
            name="Billing Eval Set v1",
            description="Core billing test suite",
            members=[
                EvalSetMemberEntry(test_case_id=s_refund.id),
                EvalSetMemberEntry(test_case_id=s_escalation.id),
            ],
        ),
    )
    sales_set = crud.create_eval_set(
        session=session,
        eval_set_in=EvalSetCreate(
            name="Sales Eval Set v1",
            description="Sales qualification test suite",
            members=[EvalSetMemberEntry(test_case_id=s_product.id)],
        ),
    )

    # Runs
    run_completed_in = RunCreate(
        name="Billing Eval — Completed",
        agent_id=agent_cs.id,
        agent_endpoint_url=agent_cs.endpoint_url,
        eval_set_id=billing_set.id,
    )
    run_completed_in = crud.enrich_run_create_from_agent(
        session=session, run_in=run_completed_in, agent=agent_cs
    )
    run_completed = crud.create_run(
        session=session,
        run_in=run_completed_in,
        created_by=owner_id,
    )
    crud.update_run(
        session=session,
        db_run=run_completed,
        run_in=RunUpdate(status=RunStatus.COMPLETED),
    )

    run_pending_in = RunCreate(
        name="Sales Eval — Pending",
        agent_id=agent_sales.id,
        agent_endpoint_url=agent_sales.endpoint_url,
        eval_set_id=sales_set.id,
    )
    run_pending_in = crud.enrich_run_create_from_agent(
        session=session, run_in=run_pending_in, agent=agent_sales
    )
    _run_pending = crud.create_run(
        session=session,
        run_in=run_pending_in,
        created_by=owner_id,
    )

    run_failed_in = RunCreate(
        name="Billing Eval — Failed",
        agent_id=agent_cs.id,
        agent_endpoint_url=agent_cs.endpoint_url,
        eval_set_id=billing_set.id,
    )
    run_failed_in = crud.enrich_run_create_from_agent(
        session=session, run_in=run_failed_in, agent=agent_cs
    )
    run_failed = crud.create_run(
        session=session,
        run_in=run_failed_in,
        created_by=owner_id,
    )
    crud.update_run(
        session=session,
        db_run=run_failed,
        run_in=RunUpdate(status=RunStatus.FAILED),
    )

    # Test case results for the completed run
    result_refund = crud.create_test_case_result(
        session=session,
        result_in=TestCaseResultCreate(
            run_id=run_completed.id,
            test_case_id=s_refund.id,
        ),
    )
    crud.update_test_case_result(
        session=session,
        db_result=result_refund,
        result_in=TestCaseResultUpdate(
            passed=True,
            turn_count=6,
            total_latency_ms=4500,
        ),
    )

    result_escalation = crud.create_test_case_result(
        session=session,
        result_in=TestCaseResultCreate(
            run_id=run_completed.id,
            test_case_id=s_escalation.id,
        ),
    )
    crud.update_test_case_result(
        session=session,
        db_result=result_escalation,
        result_in=TestCaseResultUpdate(
            passed=False,
            turn_count=12,
            total_latency_ms=9800,
            error_message="Agent failed to transfer to supervisor",
        ),
    )


def truncate_all_tables(session: Session) -> None:
    """
    Truncate all SQLModel tables dynamically.
    """
    table_names = ", ".join(
        f'"{table.name}"' for table in SQLModel.metadata.sorted_tables
    )

    session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;"))
    session.commit()
