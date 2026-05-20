import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import VoiceSimulationJobCreate, VoiceSimulationJobUpdate
from app.models.enums import VoiceSimulationJobStatus
from app.tests.utils.eval import (
    create_test_case_fixture,
    create_test_case_result_fixture,
    create_test_eval_config,
    create_test_run,
    eval_config_members,
)
from app.tests.utils.utils import AUTH_USER_EMAIL, AUTH_USER_PASSWORD

_CANCELLABLE = (
    VoiceSimulationJobStatus.PENDING,
    VoiceSimulationJobStatus.CLAIMED,
    VoiceSimulationJobStatus.CALLING,
    VoiceSimulationJobStatus.WAITING_FOR_RESULT,
)


@pytest.fixture(autouse=True)
def _isolate_voice_jobs(db: Session) -> None:
    jobs, _count = crud.list_voice_simulation_jobs(session=db, limit=10_000)
    for job in jobs:
        if job.status in _CANCELLABLE:
            crud.update_voice_simulation_job(
                session=db,
                db_job=job,
                job_in=VoiceSimulationJobUpdate(
                    status=VoiceSimulationJobStatus.CANCELLED,
                ),
            )


def _setup_waiting_job(db: Session, *, dtmf_code: str = "99124"):
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    run = create_test_run(
        db, agent_id=eval_config.agent_id, eval_config_id=eval_config.id
    )
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    job = crud.create_voice_simulation_job(
        session=db,
        job_in=VoiceSimulationJobCreate(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code=dtmf_code,
            agent_phone_number="+15551234567",
            stt_provider="deepgram",
            stt_model="nova-3",
            tts_provider="elevenlabs",
            tts_model="eleven_flash_v2_5",
            tts_voice_id="test-voice",
        ),
    )
    job = crud.update_voice_simulation_job(
        session=db,
        db_job=job,
        job_in=VoiceSimulationJobUpdate(
            status=VoiceSimulationJobStatus.WAITING_FOR_RESULT,
            call_ended_at=datetime.now(UTC),
        ),
    )
    return job


def _submission_payload(*, dtmf_code: str = "99124") -> dict[str, object]:
    return {
        "audio_url": f"mock-dtmf://{dtmf_code}",
        "messages": [
            {"role": "user", "content": "I need help with my order."},
            {"role": "assistant", "content": "Sure, I can help with that."},
        ],
    }


def test_submit_voice_simulation_result_success(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    job = _setup_waiting_job(db, dtmf_code="99124")
    payload = _submission_payload(dtmf_code="99124")

    response = client.post(
        f"{settings.API_V1_STR}/voice-simulations/results",
        json=payload,
        cookies=auth_cookies,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job.id)
    assert body["status"] == VoiceSimulationJobStatus.COMPLETED.value
    assert body["audio_url"] == payload["audio_url"]
    assert len(body["submitted_messages"]) == len(payload["messages"])
    assert body["submitted_messages"][0]["content"] == payload["messages"][0]["content"]
    assert body["result_received_at"] is not None
    assert body["normalized_transcript"] is None


def test_submit_voice_simulation_result_idempotent(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    _setup_waiting_job(db, dtmf_code="99125")
    payload = _submission_payload(dtmf_code="99125")
    url = f"{settings.API_V1_STR}/voice-simulations/results"

    first = client.post(url, json=payload, cookies=auth_cookies)
    second = client.post(url, json=payload, cookies=auth_cookies)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_submit_voice_simulation_result_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/voice-simulations/results",
        json=_submission_payload(),
    )
    assert response.status_code == 401


def test_submit_voice_simulation_result_bearer_auth(
    client: TestClient,
    db: Session,
) -> None:
    _setup_waiting_job(db, dtmf_code="99126")
    login = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": AUTH_USER_EMAIL, "password": AUTH_USER_PASSWORD},
    )
    token = login.json()["access_token"]

    response = client.post(
        f"{settings.API_V1_STR}/voice-simulations/results",
        json=_submission_payload(dtmf_code="99126"),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_submit_voice_simulation_result_job_not_found(
    client: TestClient,
    auth_cookies: dict[str, str],
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/voice-simulations/results",
        json=_submission_payload(dtmf_code="99999"),
        cookies=auth_cookies,
    )
    assert response.status_code == 404


def test_submit_voice_simulation_result_dtmf_decode_failure(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    _setup_waiting_job(db, dtmf_code="99127")
    response = client.post(
        f"{settings.API_V1_STR}/voice-simulations/results",
        json={
            "audio_url": "mock-dtmf-fail://99127",
            "messages": [{"role": "user", "content": "hello"}],
        },
        cookies=auth_cookies,
    )
    assert response.status_code == 400


def test_submit_voice_simulation_result_rejects_pending_job(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    test_case = create_test_case_fixture(db)
    eval_config = create_test_eval_config(db, members=eval_config_members(test_case.id))
    run = create_test_run(
        db, agent_id=eval_config.agent_id, eval_config_id=eval_config.id
    )
    result = create_test_case_result_fixture(
        db, run_id=run.id, test_case_id=test_case.id
    )
    crud.create_voice_simulation_job(
        session=db,
        job_in=VoiceSimulationJobCreate(
            run_id=run.id,
            test_case_id=test_case.id,
            test_case_result_id=result.id,
            dtmf_code="99128",
            agent_phone_number="+15551234567",
            stt_provider="deepgram",
            stt_model="nova-3",
            tts_provider="elevenlabs",
            tts_model="eleven_flash_v2_5",
            tts_voice_id="test-voice",
        ),
    )

    response = client.post(
        f"{settings.API_V1_STR}/voice-simulations/results",
        json=_submission_payload(dtmf_code="99128"),
        cookies=auth_cookies,
    )
    assert response.status_code == 400


def test_get_voice_simulation_job(
    client: TestClient,
    auth_cookies: dict[str, str],
    db: Session,
) -> None:
    job = _setup_waiting_job(db, dtmf_code="99129")
    response = client.get(
        f"{settings.API_V1_STR}/voice-simulations/jobs/{job.id}",
        cookies=auth_cookies,
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(job.id)
    assert response.json()["dtmf_code"] == "99129"


def test_get_voice_simulation_job_not_found(
    client: TestClient,
    auth_cookies: dict[str, str],
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/voice-simulations/jobs/{uuid.uuid4()}",
        cookies=auth_cookies,
    )
    assert response.status_code == 404
