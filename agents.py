import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class HireMindAgents:
    def __init__(self, session_id="default", aptitude_q=2, technical_q=2, communication_q=1, resume_q=2):
        self.session_id = session_id
        self.aptitude_q = max(0, int(aptitude_q))
        self.technical_q = max(0, int(technical_q))
        self.communication_q = max(0, int(communication_q))
        self.resume_q = max(0, int(resume_q))
        self.total_rounds = self.aptitude_q + self.technical_q + self.communication_q + self.resume_q
        self.evaluations = []

    def get_interview_question(self, profile, history, current_round, weak_areas="None"):
        if current_round <= self.aptitude_q:
            focus_area = "General Aptitude (logical reasoning, problem-solving scenario - DO NOT refer to their resume)"
        elif current_round <= self.aptitude_q + self.technical_q:
            focus_area = "General Technical (core engineering concepts, coding - DO NOT refer to their resume)"
        elif current_round <= self.aptitude_q + self.technical_q + self.communication_q:
            focus_area = "General Communication (behavioral, teamwork, conflict resolution - DO NOT refer to their resume)"
        else:
            focus_area = "Resume Deep Dive (STRICTLY ask about their specific claimed projects, skills, and experience listed below)"

        system_prompt = f"""
You are HireMind, an expert technical interviewer. 

Candidate Profile:
- Name: {profile.get('name', 'Candidate')}
- Target Role: {profile.get('target_role', 'Software Engineer')}
- Skills claimed: {json.dumps(profile.get('skills', []))}
- Experience: {profile.get('experience_summary', '')}
- Notable projects: {json.dumps(profile.get('projects', []))}

Interview Configuration:
- Round: {current_round} of {self.total_rounds}
- Weak areas detected so far: {weak_areas}
- Current Focus Area: {focus_area}

Rules:
1. Ask ONE question at a time. Never ask two questions in one message.
2. Your question MUST strictly be about the Current Focus Area ({focus_area}).
3. Do NOT ask about their resume/projects UNLESS the Focus Area explicitly says "Resume Deep Dive".
4. If the evaluation agent flagged a weak area, ask a follow-up question on that area.
5. Keep questions concise — max 2 sentences.
6. Do NOT give hints or answers. Do NOT evaluate the answer yourself.
7. If Round is exactly {self.total_rounds + 1}, output exactly: "INTERVIEW_COMPLETE"
"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add history
        for user_msg, ai_msg in history:
            messages.append({"role": "assistant", "content": ai_msg})
            messages.append({"role": "user", "content": user_msg})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7
        )
        return completion.choices[0].message.content

    def evaluate_answer(self, question, answer, profile):
        system_prompt = f"""
You are a strict technical interview evaluator. 

Evaluate the candidate's answer against:
1. The question asked
2. Their resume claims: {profile.get('skills', [])}
3. Expected knowledge level for role: {profile.get('target_role', '')}

Return ONLY a JSON object with the following schema:
{{
    "scores": {{"relevance": 1-10, "depth": 1-10, "accuracy": 1-10, "communication": 1-10}},
    "overall_score": 0.0-10.0,
    "weak_areas": ["topic1", "topic2"],
    "strong_areas": ["topic1"],
    "resume_mismatch": true/false,
    "resume_mismatch_detail": "explanation or null"
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer}"}
        ]
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile", # Using 70b since it's versatile enough and gpt-oss-120b might not be accessible
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            self.evaluations.append(result)
            return result
        except Exception as e:
            return {"error": str(e), "weak_areas": []}

    def generate_feedback(self, profile):
        all_weak_areas = []
        all_strong_areas = []
        total_score = 0
        resume_mismatches = []
        
        for eval in self.evaluations:
            if "weak_areas" in eval:
                all_weak_areas.extend(eval["weak_areas"])
            if "strong_areas" in eval:
                all_strong_areas.extend(eval["strong_areas"])
            if "overall_score" in eval:
                total_score += eval["overall_score"]
            if eval.get("resume_mismatch"):
                resume_mismatches.append(eval.get("resume_mismatch_detail", "Mismatch found"))
                
        avg_score = total_score / max(1, len(self.evaluations))
        
        system_prompt = f"""
You are a career coach generating a post-interview feedback report.

Candidate: {profile.get('name', 'Candidate')} | Target Role: {profile.get('target_role', '')}
Resume Skills: {json.dumps(profile.get('skills', []))}

Interview Summary:
- Total questions: {len(self.evaluations)}
- Average score: {avg_score:.1f}/10
- All weak areas detected: {list(set(all_weak_areas))}
- All strong areas: {list(set(all_strong_areas))}
- Resume mismatches: {resume_mismatches}

Generate a structured, actionable feedback report in Markdown format with:
1. Executive summary (3 sentences)
2. Strengths (bullet points, specific)
3. Gaps vs resume claims (specific, not generic)
4. Top 3 priority areas to improve
5. Suggested 2-week study plan
6. Encouragement note

Be direct, constructive, and specific. Reference actual areas where relevant.
"""
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.4
        )
        return completion.choices[0].message.content
