from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from cbt.models import CBTExam, CBTQuestion, CBTOption, CBTAssignment

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with sample CBT exams and questions'

    def handle(self, *args, **kwargs):
        # 1. Get an author
        author = User.objects.filter(role='HR').first()
        if not author:
            author = User.objects.first()
            if not author:
                self.stdout.write(self.style.ERROR('No users found in the database. Please seed users first.'))
                return
        
        self.stdout.write(f'Using {author.email} as the exam author.')

        # 2. Create the Exam
        exam, created = CBTExam.objects.get_or_create(
            title="Annual Cybersecurity Awareness Test (Sample)",
            defaults={
                'description': "This is a seeded sample exam to test the CBT module. It covers basic cybersecurity principles.",
                'duration_minutes': 15,
                'pass_mark': 60,
                'status': 'ACTIVE',
                'created_by': author,
                'randomise_questions': True,
                'allow_multiple_attempts': True,
                'show_answers_after': True,
            }
        )

        if not created:
            self.stdout.write(self.style.WARNING(f'Exam "{exam.title}" already exists. We will still add questions if missing and assign it.'))

        # 3. Add Questions
        questions_data = [
            {
                "text": "What is the most common method hackers use to compromise passwords?",
                "marks": 1,
                "options": [
                    ("Phishing", True),
                    ("Brute Force", False),
                    ("Guessing", False),
                    ("Dictionary Attack", False),
                ]
            },
            {
                "text": "Why is it important to keep your software up to date?",
                "marks": 1,
                "options": [
                    ("To get the latest UI changes", False),
                    ("To patch known security vulnerabilities", True),
                    ("To free up disk space", False),
                    ("To increase internet speed", False),
                ]
            },
            {
                "text": "Which of the following is a strong password?",
                "marks": 1,
                "options": [
                    ("password123", False),
                    ("admin", False),
                    ("P@ssw0rd2026!", True),
                    ("12345678", False),
                ]
            },
            {
                "text": "What should you do if you receive an unexpected email with an attachment from an unknown sender?",
                "marks": 2,
                "options": [
                    ("Open it immediately", False),
                    ("Forward it to a colleague", False),
                    ("Delete it or report it to IT", True),
                    ("Reply and ask who they are", False),
                ]
            },
            {
                "text": "Multi-Factor Authentication (MFA) adds a layer of security by requiring what?",
                "marks": 2,
                "options": [
                    ("Two or more verification methods", True),
                    ("A longer password", False),
                    ("A biometric scan only", False),
                    ("Approval from your manager", False),
                ]
            }
        ]

        questions_created = 0
        for q_data in questions_data:
            question, q_created = CBTQuestion.objects.get_or_create(
                exam=exam,
                text=q_data['text'],
                defaults={'marks': q_data['marks']}
            )
            if q_created:
                questions_created += 1
                for opt_text, is_correct in q_data['options']:
                    CBTOption.objects.create(
                        question=question,
                        text=opt_text,
                        is_correct=is_correct
                    )

        if questions_created > 0:
            self.stdout.write(self.style.SUCCESS(f'Created {questions_created} new questions for the exam.'))
        else:
            self.stdout.write(self.style.SUCCESS('Questions already exist for this exam.'))

        # 4. Assign the Exam to all staff
        assignment, a_created = CBTAssignment.objects.get_or_create(
            exam=exam,
            defaults={
                'assign_to_all': True
            }
        )

        if a_created:
            self.stdout.write(self.style.SUCCESS('Assigned the exam to all staff.'))
        else:
            # If it already exists, make sure it's assigned to all
            assignment.assign_to_all = True
            assignment.save()
            self.stdout.write(self.style.SUCCESS('Ensured the exam is assigned to all staff.'))

        self.stdout.write(self.style.SUCCESS('\nSuccessfully seeded the CBT data!'))
