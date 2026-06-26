import os
import json
import random
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class HireMindAgents:
    def __init__(self, session_id="default", aptitude_q=2, technical_q=2, communication_q=1, resume_q=2, target_role="", candidate_domain="", aptitude_types=""):
        self.session_id = session_id
        self.aptitude_q = max(0, int(aptitude_q))
        self.technical_q = max(0, int(technical_q))
        self.communication_q = max(0, int(communication_q))
        self.resume_q = max(0, int(resume_q))
        self.total_rounds = self.aptitude_q + self.technical_q + self.communication_q + self.resume_q
        self.evaluations = []
        self.asked_topics = []  # Track all topic summaries to prevent repetition
        self.asked_companies = []  # Track company names for each question
        self.target_role = target_role
        self.candidate_domain = candidate_domain
        
        # Parse aptitude types as a clean list
        if aptitude_types:
            self.aptitude_types = [t.strip() for t in aptitude_types.split(",") if t.strip()]
        else:
            self.aptitude_types = ["numerical", "quantitative", "logical", "verbal", "abstract"]

    def _extract_topic_hint(self, question_text):
        """Ask LLM to summarize topic of a question in 2-4 words."""
        try:
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Summarize the core concept/topic of this interview question in 2-4 words only. Return just the topic phrase."},
                    {"role": "user", "content": question_text}
                ],
                temperature=0,
                max_tokens=15
            )
            return r.choices[0].message.content.strip()
        except:
            return ""

    def get_interview_question(self, profile, history, current_round, weak_areas="None"):
        if current_round > self.total_rounds:
            return {
                "question": "INTERVIEW_COMPLETE",
                "explanation": "",
                "ideal_answer": ""
            }

        # Resolve role and domain from input values or profile fallback
        role_name = self.target_role or profile.get("target_role", "Software Engineer")
        domain_name = self.candidate_domain or profile.get("candidate_domain", "Tech")

        if current_round <= self.aptitude_q:
            # Pick a type from the list
            apt_type = self.aptitude_types[(current_round - 1) % len(self.aptitude_types)]
            focus_area = f"Aptitude ({apt_type.title()})"
            focus_detail = (
                f"Ask a single {apt_type} aptitude question. "
                f"Tailor the scenario or context of this puzzle/question to be relevant to a candidate aiming for a "
                f"'{role_name}' role in the '{domain_name}' domain. "
                f"For example, frame a mathematical, logic, or situational reasoning puzzle around business operations, "
                f"code development, scaling, or product design corresponding to that role/domain. "
                f"Do NOT reference the candidate's resume or skills directly."
            )
        elif current_round <= self.aptitude_q + self.technical_q:
            focus_area = "Technical"
            focus_detail = (
                f"Ask a core technical engineering, programming, or domain-specific question highly relevant to a "
                f"'{role_name}' role in the '{domain_name}' domain. "
                f"Test concepts like data structures, system design, architecture, or domain-specific best practices. "
                f"Do NOT reference the candidate's resume directly."
            )
        elif current_round <= self.aptitude_q + self.technical_q + self.communication_q:
            focus_area = "Communication / Behavioral"
            focus_detail = (
                f"Ask a behavioral or situational communication question about teamwork, client relations, conflict resolution, "
                f"or trade-offs relevant to a '{role_name}' working in the '{domain_name}' domain."
            )
        else:
            focus_area = "Resume Deep Dive"
            focus_detail = (
                f"You MUST ask specifically about one of the candidate's own claimed projects, experiences, or skills listed in their profile below. "
                f"Connect this back to how it fits the target role of '{role_name}' in the '{domain_name}' domain."
            )

        # Build a concise summary of already-asked topics for the LLM
        asked_summary = ", ".join(self.asked_topics) if self.asked_topics else "None yet"

        # Gather the last candidate answer (if any) for conversational flow
        last_answer = ""
        if history:
            for msg in reversed(history):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    last_answer = msg["content"]
                    break

        system_prompt = f"""You are HireMind, a warm, professional, and experienced senior technical interviewer conducting a structured live interview.
 
CANDIDATE PROFILE:
- Name: {profile.get('name', 'Candidate')}
- Target Role: {profile.get('target_role', 'Software Engineer')}
- Skills Claimed: {json.dumps(profile.get('skills', []))}
- Experience Summary: {profile.get('experience_summary', 'Not provided')}
- Notable Projects: {json.dumps(profile.get('projects', []))}
 
INTERVIEW STATE:
- Round: {current_round} of {self.total_rounds}
- Focus Area: {focus_area}
- Instruction: {focus_detail}
- Weak areas identified so far: {weak_areas}
- Topics ALREADY ASKED (DO NOT repeat or overlap): [{asked_summary}]
 
LAST CANDIDATE ANSWER: "{last_answer}"
 
STRICT RULES:
1. Ask exactly ONE question. No compound questions.
2. The question MUST explore a brand new concept — NEVER overlap with any topic in the "already asked" list.
3. If the candidate just answered something, naturally acknowledge it briefly (1 sentence max) before asking the next question. Keep it human.
4. For Resume Deep Dive rounds: you MUST reference a specific project, skill, or experience from the candidate's profile. Do not ask generic questions.
5. Keep the question concise — 1-3 sentences max.
6. Do NOT give hints, reveal the answer, or ask the question and immediately explain it.
7. Maintain an encouraging, respectful, and professional tone throughout.
8. The question must be a realistic question asked in real interviews at major MNCs (like Zoho, Google, Microsoft, Amazon, Meta, TCS, Infosys, Wipro, Cognizant, etc.) that matches this candidate's target role, domain, and experience level.
 
Return a JSON object with exactly this schema:
{{
    "question": "Your single, concise interview question here",
    "explanation": "A clear educational explanation of the concept being tested — suitable for the candidate to study later. 2-4 sentences.",
    "ideal_answer": "What a strong candidate would say. Specific, detailed, and demonstrates deep understanding. 3-6 sentences.",
    "company": "Name of the MNC that has asked this question (e.g., Zoho, Google, Microsoft, Amazon, Meta, TCS, Infosys, Wipro, Cognizant, etc.)"
}}"""
 
        messages = [{"role": "system", "content": system_prompt}]
 
        # Feed the entire flat role-based history
        if history:
            if isinstance(history[0], dict):
                messages.extend(history)
            else:
                for user_msg, ai_msg in history:
                    if ai_msg:
                        messages.append({"role": "assistant", "content": ai_msg})
                    if user_msg:
                        messages.append({"role": "user", "content": user_msg})
 
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.75,
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            # Record the topic of the question asked
            topic = self._extract_topic_hint(result.get("question", ""))
            if topic:
                self.asked_topics.append(topic)
            
            # Record company name
            company = result.get("company", "MNC")
            self.asked_companies.append(company)
            return result
        except Exception as e:
            fallback_company = "TCS"
            fallback_q = f"Could you walk me through a challenging technical problem you solved recently as a {profile.get('target_role', 'Software Engineer')}?"
            self.asked_companies.append(fallback_company)
            return {
                "question": fallback_q,
                "explanation": "This question tests problem-solving methodology, debugging skills, and the ability to communicate complex technical work clearly.",
                "ideal_answer": "I would describe the problem context, the approach I took to debug and isolate the issue, the solution I implemented, and what I learned from the experience.",
                "company": fallback_company
            }
 
    def evaluate_answer(self, question, answer, profile):
        system_prompt = f"""You are a professional technical interview evaluator.
 
Evaluate the following candidate answer thoroughly and fairly.
 
Context:
- Question Asked: {question}
- Candidate's Target Role: {profile.get('target_role', 'Software Engineer')}
- Skills Claimed on Resume: {json.dumps(profile.get('skills', []))}
 
Evaluation Criteria:
1. Relevance — Did they answer the question asked?
2. Depth — Did they show real understanding, or was it surface-level?
3. Accuracy — Was the technical content correct?
4. Communication — Was the answer clear and well-structured?
5. Resume Match — Does the answer quality match their claimed skills?
 
Return ONLY a valid JSON object with this exact schema:
{{
    "scores": {{"relevance": 1-10, "depth": 1-10, "accuracy": 1-10, "communication": 1-10}},
    "overall_score": 0.0-10.0,
    "weak_areas": ["specific topic 1", "specific topic 2"],
    "strong_areas": ["specific topic 1"],
    "resume_mismatch": true_or_false,
    "resume_mismatch_detail": "Explanation of mismatch if any, or null",
    "question": "{question.replace('"', "'")[:200]}",
    "candidate_answer": "{answer.replace('"', "'")[:400]}",
    "feedback": "2-3 sentences of specific, honest feedback on this answer."
}}"""
 
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Answer given by the candidate:\n\n{answer}"}
        ]
 
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            # Ensure question/answer are stored even if LLM omits them
            result.setdefault("question", question[:200])
            result.setdefault("candidate_answer", answer[:400])
            result.setdefault("feedback", "No specific feedback provided.")
            
            # Map the company name to this evaluation
            company = "MNC"
            idx = len(self.evaluations)
            if idx < len(self.asked_companies):
                company = self.asked_companies[idx]
            result["company"] = company
            
            self.evaluations.append(result)
            return result
        except Exception as e:
            company = "MNC"
            idx = len(self.evaluations)
            if idx < len(self.asked_companies):
                company = self.asked_companies[idx]
            fallback = {
                "scores": {"relevance": 5, "depth": 5, "accuracy": 5, "communication": 5},
                "overall_score": 5.0,
                "weak_areas": [],
                "strong_areas": [],
                "resume_mismatch": False,
                "resume_mismatch_detail": None,
                "question": question[:200],
                "candidate_answer": answer[:400],
                "feedback": f"Evaluation error: {str(e)}",
                "company": company
            }
            self.evaluations.append(fallback)
            return fallback

    def generate_feedback(self, profile):
        all_weak_areas = []
        all_strong_areas = []
        total_score = 0
        resume_mismatches = []
        round_details = []

        for i, ev in enumerate(self.evaluations):
            if "weak_areas" in ev:
                all_weak_areas.extend(ev["weak_areas"])
            if "strong_areas" in ev:
                all_strong_areas.extend(ev["strong_areas"])
            if "overall_score" in ev:
                total_score += ev["overall_score"]
            if ev.get("resume_mismatch"):
                resume_mismatches.append(ev.get("resume_mismatch_detail", "Mismatch noted"))
            round_details.append(
                f"Q{i+1}: {ev.get('question', 'N/A')} | Score: {ev.get('overall_score', '?')}/10 | "
                f"Weak: {', '.join(ev.get('weak_areas', [])) or 'none'} | "
                f"Strong: {', '.join(ev.get('strong_areas', [])) or 'none'}"
            )

        avg_score = total_score / max(1, len(self.evaluations))
        unique_weak = list(set(all_weak_areas))
        unique_strong = list(set(all_strong_areas))

        system_prompt = f"""You are a warm, senior engineering manager and career mentor. You have just interviewed {profile.get('name', 'the candidate')} for a {profile.get('target_role', 'Software Engineer')} role, and you are now writing them a detailed, personal, and honest feedback letter.

INTERVIEW DATA:
- Candidate: {profile.get('name', 'Candidate')}
- Applied For: {profile.get('target_role', 'Software Engineer')}
- Resume Skills: {json.dumps(profile.get('skills', []))}
- Overall Average Score: {avg_score:.1f} / 10.0
- Strong Areas: {unique_strong}
- Areas Needing Improvement: {unique_weak}
- Resume vs. Answer Mismatches: {resume_mismatches if resume_mismatches else 'None detected'}

ROUND-BY-ROUND BREAKDOWN:
{chr(10).join(round_details)}

WRITING INSTRUCTIONS:
1. Start with "Dear [First Name]," and write in a warm, direct, human voice — like a mentor, not a machine.
2. Open with a genuine overall impression (2-3 sentences) based on the average score.
3. Write a flowing narrative — highlight 2-3 specific things they did well and WHY it stood out. Reference actual questions/topics.
4. Honestly address weak areas — don't sugarcoat, but be constructive and specific about what was missing and how to improve.
5. If there were resume mismatches (claimed skills vs. actual answers), address it directly but kindly.
6. End with a concrete, prioritized 2-week study plan tailored to their weak areas and the target role.
7. Close with an encouraging sign-off from the "HireMind Interview Team".
8. Write in continuous paragraphs — NO bullet-point lists, NO markdown headers, NO numbered sections. Just honest, flowing prose.
9. Length: 4-6 natural paragraphs."""

        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}],
                temperature=0.5
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Dear {profile.get('name', 'Candidate')},\n\nThank you for completing the HireMind interview. Your average score was {avg_score:.1f}/10. Please review your weak areas: {', '.join(unique_weak) or 'none identified'}.\n\nBest of luck in your preparation!\n\nHireMind Interview Team"
