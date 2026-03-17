
# rag.py — Simple RAG stub for medicine lookups

class RAG:
    def retrieve(self, query: str) -> str:
        """
        Simple medicine knowledge base.
        Replace with real vector DB later.
        """
        medicine_info = {
            "tylenol": "Tylenol (acetaminophen): Max 4g/day. Avoid alcohol.",
            "advil": "Advil (ibuprofen): Take with food. Max 1200mg/day OTC.",
            "aspirin": "Aspirin: 325-650mg every 4hrs. Avoid if under 18.",
            "metformin": "Metformin: Take with meals. Monitor blood sugar.",
            "lisinopril": "Lisinopril: Take same time daily. Monitor blood pressure.",
            "atorvastatin": "Atorvastatin: Take at night. Avoid grapefruit.",
            "omeprazole": "Omeprazole: Take 30-60 mins before eating.",
            "amoxicillin": "Amoxicillin: Complete full course. Take every 8hrs.",
        }

        query_lower = query.lower()
        for drug, info in medicine_info.items():
            if drug in query_lower:
                return info

        return ""

# Single shared instance
rag = RAG()
