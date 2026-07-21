from django.test import TestCase

from support_chat.models import (
    ChatMessage,
    ChatSession,
    UnansweredQuestion,
)


class ChatSessionModelTests(TestCase):
    def test_new_session_uses_safe_defaults(self):
        session = ChatSession.objects.create()

        self.assertEqual(session.channel, "website")
        self.assertFalse(session.privacy_acknowledged)
        self.assertEqual(
            session.outcome,
            ChatSession.Outcome.IN_PROGRESS,
        )
        self.assertEqual(
            session.resolution_path,
            ChatSession.ResolutionPath.NONE,
        )
        self.assertIsNone(session.ended_at)

    def test_session_string_contains_session_id(self):
        session = ChatSession.objects.create()

        self.assertEqual(
            str(session),
            f"Chat {session.session_id}",
        )


class ChatMessageModelTests(TestCase):
    def setUp(self):
        self.session = ChatSession.objects.create(
            privacy_acknowledged=True,
        )

    def test_message_stores_intent_sources_and_metadata(self):
        message = ChatMessage.objects.create(
            session=self.session,
            sender_type=ChatMessage.SenderType.ASSISTANT,
            message="Standard shipping normally takes 3-7 business days.",
            detected_intent=ChatMessage.Intent.FAQ,
            resolution_path=ChatSession.ResolutionPath.FAQ,
            source_references=[
                {
                    "source_type": "faq",
                    "source_id": "FAQ-001",
                }
            ],
            decision_metadata={
                "score": 27,
            },
        )

        self.assertEqual(
            message.detected_intent,
            ChatMessage.Intent.FAQ,
        )
        self.assertEqual(
            message.resolution_path,
            ChatSession.ResolutionPath.FAQ,
        )
        self.assertEqual(
            message.source_references[0]["source_id"],
            "FAQ-001",
        )
        self.assertEqual(
            message.decision_metadata["score"],
            27,
        )

    def test_message_json_defaults_are_empty(self):
        message = ChatMessage.objects.create(
            session=self.session,
            sender_type=ChatMessage.SenderType.CUSTOMER,
            message="Hello",
        )

        self.assertEqual(message.source_references, [])
        self.assertEqual(message.decision_metadata, {})

    def test_messages_are_deleted_with_session(self):
        ChatMessage.objects.create(
            session=self.session,
            sender_type=ChatMessage.SenderType.CUSTOMER,
            message="Hello",
        )

        self.session.delete()

        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_messages_use_creation_order(self):
        first_message = ChatMessage.objects.create(
            session=self.session,
            sender_type=ChatMessage.SenderType.CUSTOMER,
            message="First message",
        )
        second_message = ChatMessage.objects.create(
            session=self.session,
            sender_type=ChatMessage.SenderType.ASSISTANT,
            message="Second message",
        )

        self.assertEqual(
            list(ChatMessage.objects.all()),
            [
                first_message,
                second_message,
            ],
        )


class UnansweredQuestionModelTests(TestCase):
    def test_unanswered_question_uses_safe_defaults(self):
        session = ChatSession.objects.create()

        unanswered = UnansweredQuestion.objects.create(
            question="Does this shelf hold 80 pounds?",
            normalized_topic="does this shelf hold 80 pounds",
            session=session,
        )

        self.assertEqual(unanswered.occurrence_count, 1)
        self.assertEqual(
            unanswered.status,
            UnansweredQuestion.Status.OPEN,
        )
        self.assertEqual(unanswered.review_notes, "")
        self.assertIsNone(unanswered.converted_faq)

    def test_session_deletion_preserves_unanswered_question(self):
        session = ChatSession.objects.create()

        unanswered = UnansweredQuestion.objects.create(
            question="Unknown warranty question",
            normalized_topic="unknown warranty question",
            session=session,
        )

        session.delete()
        unanswered.refresh_from_db()

        self.assertIsNone(unanswered.session)
        self.assertEqual(
            UnansweredQuestion.objects.count(),
            1,
        )

    def test_highest_occurrence_question_is_listed_first(self):
        low_frequency = UnansweredQuestion.objects.create(
            question="Question one",
            normalized_topic="question one",
            occurrence_count=1,
        )
        high_frequency = UnansweredQuestion.objects.create(
            question="Question two",
            normalized_topic="question two",
            occurrence_count=5,
        )

        self.assertEqual(
            list(UnansweredQuestion.objects.all()),
            [
                high_frequency,
                low_frequency,
            ],
        )