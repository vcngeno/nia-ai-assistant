from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.schema import Document
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        """Initialize RAG service with OpenAI"""
        
        # Get API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        # Initialize embeddings and LLM
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            openai_api_key=self.api_key
        )
        
        # Set up vector store path
        self.persist_directory = "/app/chroma_db"
        
        # Load or create vector store
        self.vector_store = self._initialize_vector_store()
        
        logger.info(f"✅ RAG Service initialized with OpenAI gpt-4o")
    
    def _initialize_vector_store(self):
        """Load existing vector store or create new one from content"""
        
        # Check if vector store already exists
        if os.path.exists(self.persist_directory) and os.listdir(self.persist_directory):
            logger.info(f"📂 Loading existing vector store from {self.persist_directory}")
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        
        # Create new vector store from content
        logger.info("📚 Creating new vector store from content files...")
        return self._create_vector_store_from_content()
    
    def _create_vector_store_from_content(self):
        """Load content files and create vector store"""
        
        content_dir = "/app/content"
        
        if not os.path.exists(content_dir):
            logger.warning(f"⚠️ Content directory not found: {content_dir}")
            # Create empty vector store
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        
        # Load markdown files
        try:
            loader = DirectoryLoader(
                content_dir,
                glob="**/*.md",
                loader_cls=TextLoader,
                loader_kwargs={'encoding': 'utf-8'}
            )
            documents = loader.load()
            
            if not documents:
                logger.warning("⚠️ No content files found")
                return Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""]
            )
            
            chunks = text_splitter.split_documents(documents)
            
            # Add metadata
            for chunk in chunks:
                # Extract grade level from content if present
                content = chunk.page_content
                if "Grade Level:" in content:
                    grade_line = [line for line in content.split('\n') if 'Grade Level:' in line]
                    if grade_line:
                        chunk.metadata['grade_level'] = grade_line[0].split('Grade Level:')[1].strip()
                
                chunk.metadata['verified'] = True
            
            # Create vector store
            vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            logger.info(f"✅ Loaded {len(documents)} documents, {len(chunks)} chunks into vector store")
            
            return vector_store
            
        except Exception as e:
            logger.error(f"Error loading content: {e}", exc_info=True)
            return Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
    
    def query(
        self,
        question: str,
        grade_level: str = "5th grade",
        depth_level: int = 1,
        num_sources: int = 3
    ) -> Dict:
        """Query the RAG system with grade-appropriate prompting"""
        
        try:
            # Search for relevant content
            results = self.vector_store.similarity_search(
                question,
                k=num_sources
            )
            
            # Build context from results
            context = "\n\n".join([doc.page_content for doc in results])
            
            # Get grade-appropriate prompt
            system_prompt = self._get_grade_appropriate_prompt(grade_level, depth_level)
            
            # Format prompt with context
            full_prompt = system_prompt.replace("{context}", context)
            
            # Generate response
            response = self.llm.invoke([
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": question}
            ])
            
            # Format sources
            sources = []
            for doc in results:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "grade_level": doc.metadata.get("grade_level", "General"),
                    "source": doc.metadata.get("source", "Educational Content"),
                    "verified": doc.metadata.get("verified", True)
                })
            
            return {
                "answer": response.content,
                "sources": sources,
                "model_used": "gpt-4o"
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}", exc_info=True)
            raise
    
    def _get_grade_appropriate_prompt(self, grade_level: str, depth_level: int) -> str:
        """Generate grade and depth appropriate system prompt"""
        
        # Base guidelines by grade level
        grade_guides = {
            "K-1st": "Use very simple words (1-2 syllables). Short sentences (5-7 words). Lots of examples from daily life.",
            "2nd-3rd": "Use simple, clear language. Short paragraphs. Relate to things kids know (playground, pets, family).",
            "4th-5th": "Use clear explanations. Can include some bigger words but explain them. Give interesting examples.",
            "6th-8th": "Use more advanced vocabulary. Include deeper concepts. Make connections between ideas.",
            "9th-12th": "Use sophisticated vocabulary. Explore complex ideas. Encourage critical thinking."
        }
        
        # Determine appropriate guide
        base_guide = grade_guides.get(grade_level, grade_guides["4th-5th"])
        
        # Depth-based adjustments
        depth_guides = {
            1: "Give a brief, clear answer (2-3 sentences). Be friendly and encouraging.",
            2: "Provide more detail (4-6 sentences). Include examples and interesting facts.",
            3: "Give comprehensive explanation. Connect concepts. Include real-world applications."
        }
        
        depth_guide = depth_guides.get(depth_level, depth_guides[1])
        
        return f"""You are Nia, a warm and intelligent AI learning assistant for children.

GRADE LEVEL: {grade_level}
RESPONSE DEPTH: Level {depth_level}

GUIDELINES:
- {base_guide}
- {depth_guide}
- Always be encouraging and build confidence
- Use "you" and "your" to make it personal

⚠️ SOURCE TRANSPARENCY RULES (VERY IMPORTANT):
1. If you are answering based on the PROVIDED CONTEXT below, start your answer with:
   "📚 From my learning materials:"
   
2. If the context is empty or insufficient and you're using your general knowledge, start with:
   "ℹ️ From general knowledge:"
   
3. ALWAYS be transparent about your source

4. If using context, cite the specific material at the end

ANSWER QUALITY:
- Be factually accurate
- Use age-appropriate vocabulary for {grade_level}
- Include examples kids can relate to
- End with a curiosity-building question when appropriate

CONTEXT PROVIDED:
{{context}}

Remember: Label your source clearly at the start of your answer!"""


# Global RAG service instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get or create the global RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
