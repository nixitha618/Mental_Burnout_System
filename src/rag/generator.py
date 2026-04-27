"""
Generator module for RAG pipeline - Uses Groq AI for intelligent responses
Switched from Google Gemini to Groq (llama3-8b-8192) to avoid rate limits
"""

from typing import List, Dict, Any, Optional
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.rag.retriever import Retriever
from src.utils.logger import setup_logger
from src.utils.helpers import truncate_text

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)

# Configure Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

try:
    from groq import Groq
    GROQ_AVAILABLE = True
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Groq client configured")
    else:
        groq_client = None
        logger.warning("⚠️ GROQ_API_KEY not found in .env")
except ImportError:
    GROQ_AVAILABLE = False
    groq_client = None
    logger.warning("⚠️ groq not installed. Run: pip install groq")


class GuidanceGenerator:
    def __init__(self, use_groq: bool = True):
        self.retriever = Retriever()
        self.use_groq = use_groq and GROQ_AVAILABLE and groq_client is not None

        if self.use_groq:
            logger.info("✅ Groq AI is ready to use")
        else:
            logger.info("Using template-based generation (Groq not available)")

    def generate_guidance(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate personalized guidance using RAG + Groq"""
        logger.info(f"Generating guidance for: '{query}'")

        risk_level = user_context.get('risk_level', 'Medium') if user_context else 'Medium'

        # Retrieve relevant documents
        relevant_docs = self.retriever.retrieve(
            query,
            n_results=3,
            filter_by_risk=risk_level
        )

        if self.use_groq and relevant_docs:
            return self._generate_with_groq(query, relevant_docs, user_context)
        elif relevant_docs:
            return self._generate_template_response(query, relevant_docs, user_context)
        else:
            return self._generate_fallback_response(query, user_context)

    def _generate_with_groq(self, query: str, docs: List[Dict], user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate response using Groq AI (llama3-8b-8192)"""

        # Build context from retrieved documents
        context = "\n\n".join([f"Resource {i+1}: {doc['content']}" for i, doc in enumerate(docs[:3])])

        # Build user context string
        user_info = ""
        if user_context:
            user_info = f"""
User's Current State:
- Risk Level: {user_context.get('risk_level', 'Unknown')}
- Sleep: {user_context.get('sleep_hours', 'Unknown')} hours
- Stress Level: {user_context.get('stress_level', 'Unknown')}/10
- Workload: {user_context.get('workload_hours', 'Unknown')} hours
- Physical Activity: {user_context.get('physical_activity', 'Unknown')} mins
- Social Interaction: {user_context.get('social_interaction', 'Unknown')} hours
"""

        # Create prompt
        prompt = f"""You are a compassionate wellness assistant helping someone prevent burnout.
Provide personalized, practical guidance based on the user's question and context.

{user_info}

Relevant Wellness Information:
{context}

User Question: {query}

Instructions:
1. Be warm, empathetic, and supportive
2. Provide actionable, practical tips they can use today
3. Keep response to 3-5 sentences
4. If user has specific metrics (low sleep, high stress), address them directly
5. Do not provide medical advice - suggest consulting professionals when appropriate

Your response:"""

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",   # Fast & free on Groq
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            guidance = response.choices[0].message.content

            sources = [{'content': truncate_text(doc['content'], 100)} for doc in docs[:2]]

            return {
                'query': query,
                'guidance': guidance,
                'sources': sources,
                'context_used': user_context,
                'generation_method': 'groq_ai'
            }

        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            return self._generate_template_response(query, docs, user_context)

    def _generate_template_response(self, query: str, docs: List[Dict], user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate response using templates (fallback)"""

        risk_level = user_context.get('risk_level', 'Medium') if user_context else 'Medium'

        greetings = {
            'Low': "🌟 Great job maintaining good habits! Here are some tips to keep you on track:",
            'Medium': "⚠️ Here's some personalized guidance based on your current risk level:",
            'High': "🚨 It's important to take action. Here are some strategies that can help:"
        }
        greeting = greetings.get(risk_level, "Here's some guidance for you:")

        sources = []
        guidance_parts = [greeting]

        for i, doc in enumerate(docs[:2]):
            sources.append({
                'content': truncate_text(doc['content'], 100),
                'relevance': doc['relevance_score'],
                'metadata': doc.get('metadata', {})
            })

            category = doc.get('metadata', {}).get('category', 'Wellness').capitalize()
            tip = f"\n**{category} Tip:**\n{doc['content']}\n"
            guidance_parts.append(tip)

        if user_context:
            recommendations = self._get_personalized_recommendations(user_context)
            if recommendations:
                guidance_parts.append("\n**Personalized Recommendations:**")
                guidance_parts.extend([f"• {rec}" for rec in recommendations])

        guidance = "\n".join(guidance_parts)

        return {
            'query': query,
            'guidance': guidance,
            'sources': sources,
            'context_used': user_context,
            'generation_method': 'template'
        }

    def _generate_fallback_response(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate fallback response when no documents found"""

        risk_level = user_context.get('risk_level', 'Medium') if user_context else 'Medium'
        query_lower = query.lower()

        if 'stress' in query_lower or 'anxious' in query_lower:
            responses = {
                'Low': "🌟 To maintain low stress, continue your current habits. Regular exercise and mindfulness help keep stress at bay.",
                'Medium': "⚠️ For moderate stress, try the 4-7-8 breathing technique: inhale for 4 seconds, hold for 7, exhale for 8.",
                'High': "🚨 High stress needs attention. Try: 1) Deep breathing 2) A short walk 3) Talking to a friend 4) Consider professional support."
            }
        elif 'sleep' in query_lower or 'insomnia' in query_lower:
            responses = {
                'Low': "😴 Maintain good sleep with a consistent schedule and relaxing bedtime routine.",
                'Medium': "😴 Improve sleep by avoiding screens 1 hour before bed and keeping your bedroom cool and dark.",
                'High': "😴 For significant sleep issues: 1) No caffeine after 2pm 2) Wind-down routine 3) Consult a sleep specialist if needed."
            }
        elif 'work' in query_lower or 'balance' in query_lower or 'workload' in query_lower:
            responses = {
                'Low': "⚖️ Keep work-life balance by setting clear boundaries and taking regular breaks.",
                'Medium': "⚖️ Try time-blocking and the Pomodoro technique to manage your workload effectively.",
                'High': "⚖️ High workload? Prioritize tasks, delegate when possible, and set strict work hour boundaries."
            }
        elif 'exercise' in query_lower or 'activity' in query_lower:
            responses = {
                'Low': "🏃 Keep up the good work! Aim for 150 minutes of moderate exercise weekly.",
                'Medium': "🏃 Start with 15-20 minute walks daily and gradually increase activity.",
                'High': "🏃 Even small amounts help. Start with 10-minute walks and build up gradually."
            }
        elif 'diet' in query_lower or 'food' in query_lower or 'nutrition' in query_lower:
            responses = {
                'Low': "🥗 Maintain a balanced diet with regular meals. Stay hydrated throughout the day.",
                'Medium': "🥗 Focus on whole foods, limit processed sugars, and eat regular meals to stabilize mood.",
                'High': "🥗 Start small: drink more water, eat breakfast, add one vegetable to each meal."
            }
        elif 'social' in query_lower or 'lonely' in query_lower:
            responses = {
                'Low': "👥 Maintain social connections by scheduling regular catch-ups with friends and family.",
                'Medium': "👥 Try to connect with someone daily, even if briefly. Join groups with similar interests.",
                'High': "👥 Reach out to one person today. Consider joining a support group or community activity."
            }
        else:
            responses = {
                'Low': "🌟 Your wellness metrics look good! Continue monitoring and maintaining healthy habits.",
                'Medium': "⚠️ Focus on the area that concerns you most - small improvements make a big difference.",
                'High': "🚨 Prioritize: 1) Sleep (7-9 hours) 2) Stress management 3) Physical activity 4) Social connection."
            }

        guidance = responses.get(risk_level, responses['Medium'])

        if user_context:
            personal_note = self._get_personalized_note(user_context)
            if personal_note:
                guidance += f"\n\n💡 **Personal Note:** {personal_note}"

        return {
            'query': query,
            'guidance': guidance,
            'sources': [],
            'context_used': user_context,
            'generation_method': 'intelligent_fallback'
        }

    def _get_personalized_recommendations(self, context: Dict) -> List[str]:
        recommendations = []
        if context.get('sleep_hours') and float(context['sleep_hours']) < 6:
            recommendations.append("Your sleep is below recommended levels. Try to get 7-9 hours.")
        if context.get('stress_level') and int(context['stress_level']) > 7:
            recommendations.append("Your stress is high. Consider meditation or deep breathing.")
        if context.get('workload_hours') and float(context['workload_hours']) > 10:
            recommendations.append("Your workload is high. Set boundaries and take regular breaks.")
        if context.get('physical_activity') and int(context['physical_activity']) < 20:
            recommendations.append("Aim for at least 20-30 minutes of physical activity daily.")
        if context.get('social_interaction') and float(context['social_interaction']) < 1:
            recommendations.append("Try to connect with others daily, even if briefly.")
        return recommendations

    def _get_personalized_note(self, context: Dict) -> str:
        notes = []
        if context.get('sleep_hours') and float(context.get('sleep_hours', 8)) < 6:
            notes.append("You're getting less than 6 hours of sleep - this is a key area to improve.")
        if context.get('stress_level') and int(context.get('stress_level', 0)) > 7:
            notes.append("Your stress level is high - stress management tips are especially important for you.")
        if context.get('workload_hours') and float(context.get('workload_hours', 0)) > 10:
            notes.append("Your workload is high - consider setting firmer boundaries.")
        if context.get('physical_activity') and int(context.get('physical_activity', 30)) < 20:
            notes.append("Try to increase physical activity - even short walks help.")
        if context.get('social_interaction') and float(context.get('social_interaction', 2)) < 1:
            notes.append("Social connection is important - try to reach out to someone today.")
        return " ".join(notes[:2]) if notes else ""


_generator = None

def get_generator(use_groq: bool = True) -> GuidanceGenerator:
    global _generator
    if _generator is None:
        _generator = GuidanceGenerator(use_groq=use_groq)
    return _generator


if __name__ == "__main__":
    print("=" * 50)
    print("Testing RAG Generator with Groq")
    print("=" * 50)

    if not GROQ_API_KEY:
        print("\n❌ GROQ_API_KEY not found in .env file")
        print("Please add: GROQ_API_KEY=your_groq_key_here")
    else:
        print(f"\n✅ GROQ_API_KEY found: {GROQ_API_KEY[:10]}...")

    generator = get_generator(use_groq=True)

    test_query = "I'm feeling very stressed at work and can't sleep well"
    test_context = {
        "risk_level": "High",
        "sleep_hours": 5,
        "stress_level": 9,
        "workload_hours": 12
    }

    result = generator.generate_guidance(test_query, test_context)
    print(f"\n📝 Query: {test_query}")
    print(f"🔧 Method: {result['generation_method']}")
    print(f"\n💬 Response:\n{result['guidance']}")