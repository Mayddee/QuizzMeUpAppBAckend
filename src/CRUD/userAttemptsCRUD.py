# routers/attempts.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.DatabaseManager.queries import get_session
from src.Schemas.QuizShema import QuizAttemptCreate, QuizAttemptResult, UserAnswerRead, QuestionType, CorrectAnswerInfo, \
    UserRanking
from src.Models.models import Quiz, Question, Answer, UserAnswer, QuizAttempt, User
from src.CRUD.userCRUD import get_current_user_id_from_cookie

router = APIRouter()

# @router.post("/quiz/{quiz_id}/attempt", response_model=QuizAttemptResult)
# async def submit_quiz_attempt(
#     quiz_id: int,
#     data: QuizAttemptCreate,
#     session: AsyncSession = Depends(get_session),
#     user_id: int = Depends(get_current_user_id_from_cookie)
# ):
#     quiz_result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
#     quiz = quiz_result.scalar_one_or_none()
#     if not quiz:
#         raise HTTPException(status_code=404, detail="Quiz not found")
#
#     question_result = await session.execute(select(Question).where(Question.quiz_id == quiz_id))
#     questions = {q.id: q for q in question_result.scalars().all()}
#     if not questions:
#         raise HTTPException(status_code=400, detail="No questions in this quiz")
#
#     all_question_ids = list(questions.keys())
#     answer_result = await session.execute(select(Answer).where(Answer.question_id.in_(all_question_ids)))
#     all_answers = answer_result.scalars().all()
#
#     correct_ids_map: dict[int, list[int]] = {}
#     for ans in all_answers:
#         if ans.is_correct:
#             correct_ids_map.setdefault(ans.question_id, []).append(ans.id)
#
#     attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id, score=0)
#     session.add(attempt)
#     await session.flush()
#     attempt_id = attempt.id
#
#     total_score = 0
#     max_score = 0
#     user_answer_reads = []
#
#     for user_answer in data.answers:
#         question = questions.get(user_answer.question_id)
#         if not question:
#             continue
#
#         max_score += question.points
#         points_awarded = 0
#         is_correct = False
#
#         submitted_ids = user_answer.selected_answer_ids or []
#         correct_ids = sorted(correct_ids_map.get(question.id, []))
#
#         if question.type == QuestionType.text:
#             is_correct = True
#             points_awarded = question.points
#
#         elif question.type == QuestionType.single:
#             if len(correct_ids) == 1 and len(submitted_ids) == 1 and submitted_ids[0] == correct_ids[0]:
#                 is_correct = True
#                 points_awarded = question.points
#
#         elif question.type == QuestionType.multiple:
#             if sorted(submitted_ids) == correct_ids:
#                 is_correct = True
#                 points_awarded = question.points
#
#         # Сохранение ответа в базу
#         session.add(UserAnswer(
#             attempt_id=attempt_id,
#             question_id=user_answer.question_id,
#             answer_text=user_answer.answer_text,
#             selected_answer_ids=submitted_ids
#         ))
#
#         total_score += points_awarded
#
#         user_answer_reads.append(UserAnswerRead(
#             question_id=user_answer.question_id,
#             answer_text=user_answer.answer_text,
#             selected_answer_ids=submitted_ids,
#             is_correct=is_correct,
#             points_awarded=points_awarded
#         ))
#
#     attempt.score = total_score
#     await session.commit()
#
#     return QuizAttemptResult(
#         attempt_id=attempt_id,
#         score=total_score,
#         max_score=max_score,
#         answers=user_answer_reads
#     )

@router.post("/quiz/{quiz_id}/attempt", response_model=QuizAttemptResult)
async def submit_quiz_attempt(
    quiz_id: int,
    data: QuizAttemptCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id_from_cookie)
):
    quiz_result = await session.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = quiz_result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question_result = await session.execute(select(Question).where(Question.quiz_id == quiz_id))
    questions = {q.id: q for q in question_result.scalars().all()}
    if not questions:
        raise HTTPException(status_code=400, detail="No questions in this quiz")

    all_question_ids = list(questions.keys())
    answer_result = await session.execute(select(Answer).where(Answer.question_id.in_(all_question_ids)))
    all_answers = answer_result.scalars().all()

    # Построим словарь правильных ответов
    correct_ids_map: dict[int, list[int]] = {}
    for ans in all_answers:
        if ans.is_correct:
            correct_ids_map.setdefault(ans.question_id, []).append(ans.id)

    attempt = QuizAttempt(user_id=user_id, quiz_id=quiz_id, score=0)
    session.add(attempt)
    await session.flush()
    attempt_id = attempt.id

    total_score = 0
    max_score = 0
    user_answer_reads = []

    for user_answer in data.answers:
        question = questions.get(user_answer.question_id)
        if not question:
            continue

        submitted_ids = user_answer.selected_answer_ids or []
        correct_ids = sorted(correct_ids_map.get(question.id, []))
        is_correct = False
        points_awarded = 0

        max_score += question.points

        q_type = question.type.value if hasattr(question.type, "value") else str(question.type)

        if q_type == "text":
            is_correct = True
            points_awarded = question.points

        elif q_type == "single":
            if len(correct_ids) == 1 and len(submitted_ids) == 1 and submitted_ids[0] == correct_ids[0]:
                is_correct = True
                points_awarded = question.points

        elif q_type == "multiple":
            if sorted(submitted_ids) == correct_ids:
                is_correct = True
                points_awarded = question.points

        session.add(UserAnswer(
            attempt_id=attempt_id,
            question_id=user_answer.question_id,
            answer_text=user_answer.answer_text,
            selected_answer_ids=submitted_ids
        ))

        total_score += points_awarded

        user_answer_reads.append(UserAnswerRead(
            question_id=user_answer.question_id,
            question_text=question.text,
            answer_text=user_answer.answer_text,
            selected_answer_ids=submitted_ids,
            is_correct=is_correct,
            points_awarded=points_awarded
        ))

    attempt.score = total_score
    await session.commit()

    return QuizAttemptResult(
        attempt_id=attempt_id,
        score=total_score,
        max_score=max_score,
        answers=user_answer_reads
    )



@router.get("/attempts/{attempt_id}", response_model=QuizAttemptResult)
async def get_quiz_attempt_result(
    attempt_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id_from_cookie)
):
    attempt = await session.get(QuizAttempt, attempt_id)
    if not attempt or attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    answers_result = await session.execute(
        select(UserAnswer).where(UserAnswer.attempt_id == attempt_id)
    )
    answers = answers_result.scalars().all()

    question_ids = [a.question_id for a in answers]
    questions_result = await session.execute(
        select(Question).where(Question.id.in_(question_ids))
    )
    questions = {q.id: q for q in questions_result.scalars().all()}

    answer_result = await session.execute(
        select(Answer).where(Answer.question_id.in_(questions.keys()))
    )
    answer_map = {}
    for a in answer_result.scalars().all():
        answer_map.setdefault(a.question_id, []).append(a)

    result_answers = []

    for ua in answers:
        question = questions.get(ua.question_id)
        if not question:
            continue

        q_type = question.type.value if hasattr(question.type, "value") else str(question.type)
        is_correct = False

        if q_type == "text":
            is_correct = True
        elif q_type == "single":
            correct = next((a for a in answer_map[question.id] if a.is_correct), None)
            if correct and ua.selected_answer_ids == [correct.id]:
                is_correct = True
        elif q_type == "multiple":
            correct_ids = sorted([a.id for a in answer_map[question.id] if a.is_correct])
            user_ids = sorted(ua.selected_answer_ids or [])
            if correct_ids == user_ids:
                is_correct = True

        result_answers.append(UserAnswerRead(
            question_id=ua.question_id,
            question_text=question.text,
            answer_text=ua.answer_text,
            selected_answer_ids=ua.selected_answer_ids,
            is_correct=is_correct,
            points_awarded=question.points if is_correct else 0
        ))

    return QuizAttemptResult(
        attempt_id=attempt.id,
        score=attempt.score,
        max_score=sum(q.points for q in questions.values()),
        answers=result_answers,
    )

@router.get("/attempts/{attempt_id}/correct-answers", response_model=List[CorrectAnswerInfo])
async def get_correct_answers(
    attempt_id: int,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id_from_cookie)
):
    attempt = await session.get(QuizAttempt, attempt_id)
    if not attempt or attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Получаем вопросы
    answers_result = await session.execute(
        select(UserAnswer).where(UserAnswer.attempt_id == attempt_id)
    )
    answers = answers_result.scalars().all()
    question_ids = [a.question_id for a in answers]

    question_result = await session.execute(
        select(Question).where(Question.id.in_(question_ids))
    )
    questions = {q.id: q for q in question_result.scalars().all()}

    answer_result = await session.execute(
        select(Answer).where(Answer.question_id.in_(question_ids))
    )
    correct_answers_by_question: dict[int, list[str]] = {}
    for a in answer_result.scalars().all():
        if a.is_correct:
            correct_answers_by_question.setdefault(a.question_id, []).append(a.text)

    return [
        CorrectAnswerInfo(
            id=q.id,
            text=q.text,
            correct_answers=correct_answers_by_question.get(q.id, [])
        )
        for q in questions.values()
    ]

@router.get("/rankings", response_model=List[UserRanking])
async def get_user_rankings(session: AsyncSession = Depends(get_session)):

    # подзапрос: лучший результат юзера по каждому квизу
    subq = (
        select(
            QuizAttempt.user_id,
            QuizAttempt.quiz_id,
            func.max(QuizAttempt.score).label("best_score")
        )
        .group_by(QuizAttempt.user_id, QuizAttempt.quiz_id)
        .subquery()
    )

    # основной запрос: суммируем лучшие результаты
    stmt = (
        select(
            subq.c.user_id,
            User.username,
            func.sum(subq.c.best_score).label("total_score")
        )
        .join(User, User.id == subq.c.user_id)
        .group_by(subq.c.user_id, User.username)
        .order_by(func.sum(subq.c.best_score).desc())
        .limit(50)
    )

    result = await session.execute(stmt)

    return [
        UserRanking(
            user_id=row.user_id,
            username=row.username,
            total_score=row.total_score
        )
        for row in result.all()
    ]
