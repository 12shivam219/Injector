"""
Requirements Integration Module for Resume Customizer
Provides intelligent integration between job requirements and resume customization
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Tuple
import re
from datetime import datetime
from dataclasses import dataclass

from ui.requirements_manager import RequirementsManager
from infrastructure.utilities.logger import get_logger
from resume_customizer.parsers.text_parser import parse_input_text

logger = get_logger()

@dataclass
class TechStackRecommendation:
    """Recommendation for tech stack based on job requirements."""
    tech_name: str
    confidence: float
    suggested_points: List[str]
    reasoning: str

@dataclass
class ResumeCustomizationPlan:
    """Plan for customizing resume based on specific job requirement."""
    requirement_id: str
    job_title: str
    client: str
    recommended_tech_stacks: List[TechStackRecommendation]
    focus_areas: List[str]
    estimated_points: int

class RequirementsAnalyzer:
    """Analyzes job requirements to suggest resume customizations."""
    
    # Technology mapping based on common job requirements
    TECH_MAPPING = {
        'python': {
            'keywords': ['python', 'django', 'flask', 'pandas', 'numpy', 'pytest'],
            'points': [
                'Developed scalable Python applications using Django/Flask frameworks',
                'Implemented data processing pipelines with Pandas and NumPy',
                'Created comprehensive test suites using Pytest and unittest',
                'Built RESTful APIs with Python for microservices architecture'
            ]
        },
        'javascript': {
            'keywords': ['javascript', 'js', 'react', 'node', 'angular', 'vue'],
            'points': [
                'Developed interactive web applications using React/Angular/Vue',
                'Built server-side applications with Node.js and Express',
                'Implemented responsive UI components with modern JavaScript ES6+',
                'Created real-time applications using WebSocket and Socket.io'
            ]
        },
        'java': {
            'keywords': ['java', 'spring', 'hibernate', 'maven', 'gradle'],
            'points': [
                'Developed enterprise applications using Java and Spring Framework',
                'Implemented data persistence layer with Hibernate ORM',
                'Built microservices architecture using Spring Boot and Spring Cloud',
                'Created robust backend systems with Java 8+ features and streams'
            ]
        },
        'aws': {
            'keywords': ['aws', 'amazon', 'ec2', 's3', 'lambda', 'cloud'],
            'points': [
                'Deployed and managed applications on AWS EC2 instances',
                'Implemented serverless architectures using AWS Lambda and API Gateway',
                'Designed scalable storage solutions with S3 and CloudFront',
                'Set up CI/CD pipelines using AWS CodePipeline and CodeDeploy'
            ]
        },
        'docker': {
            'keywords': ['docker', 'container', 'kubernetes', 'k8s'],
            'points': [
                'Containerized applications using Docker for consistent deployments',
                'Orchestrated microservices with Kubernetes and Helm charts',
                'Implemented container security best practices and image optimization',
                'Set up automated container builds and deployments'
            ]
        },
        'sql': {
            'keywords': ['sql', 'database', 'mysql', 'postgresql', 'oracle'],
            'points': [
                'Designed and optimized complex SQL queries and stored procedures',
                'Implemented database schemas and normalized data structures',
                'Performed database performance tuning and query optimization',
                'Created data migration scripts and ETL processes'
            ]
        }
    }
    
    def __init__(self):
        self.requirements_manager = RequirementsManager()
    
    def analyze_job_requirement(self, requirement_id: str) -> Optional[ResumeCustomizationPlan]:
        """
        Analyze a job requirement and create a resume customization plan.
        
        Args:
            requirement_id: ID of the job requirement to analyze
            
        Returns:
            ResumeCustomizationPlan or None if requirement not found
        """
        requirement = self.requirements_manager.get_requirement(requirement_id)
        if not requirement:
            return None
            
        job_title = requirement.get('job_title', '')
        client = requirement.get('client', '')
        
        # Extract tech requirements from job title and other fields
        tech_keywords = self._extract_tech_keywords(requirement)
        
        # Generate tech stack recommendations
        recommendations = self._generate_tech_recommendations(tech_keywords, job_title)
        
        # Determine focus areas
        focus_areas = self._determine_focus_areas(job_title, recommendations)
        
        # Estimate total points that will be added
        estimated_points = sum(len(rec.suggested_points) for rec in recommendations)
        
        return ResumeCustomizationPlan(
            requirement_id=requirement_id,
            job_title=job_title,
            client=client,
            recommended_tech_stacks=recommendations,
            focus_areas=focus_areas,
            estimated_points=estimated_points
        )
    
    def _extract_tech_keywords(self, requirement: Dict[str, Any]) -> List[str]:
        """Extract technology keywords from job requirement."""
        text_fields = [
            requirement.get('job_title', ''),
            requirement.get('next_steps', ''),
            # Could add more fields like job description if available
        ]
        
        combined_text = ' '.join(text_fields).lower()
        
        found_keywords = []
        for tech_category, tech_info in self.TECH_MAPPING.items():
            for keyword in tech_info['keywords']:
                if keyword in combined_text:
                    found_keywords.append(tech_category)
                    break
        
        return found_keywords
    
    def _generate_tech_recommendations(self, tech_keywords: List[str], job_title: str) -> List[TechStackRecommendation]:
        """Generate technology stack recommendations based on keywords."""
        recommendations = []
        
        for tech_keyword in tech_keywords:
            if tech_keyword in self.TECH_MAPPING:
                tech_info = self.TECH_MAPPING[tech_keyword]
                
                # Calculate confidence based on job title relevance
                confidence = self._calculate_confidence(tech_keyword, job_title)
                
                recommendation = TechStackRecommendation(
                    tech_name=tech_keyword.title(),
                    confidence=confidence,
                    suggested_points=tech_info['points'][:3],  # Top 3 points
                    reasoning=f"Detected {tech_keyword} requirements in job title/description"
                )
                recommendations.append(recommendation)
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        return recommendations
    
    def _calculate_confidence(self, tech_keyword: str, job_title: str) -> float:
        """Calculate confidence score for a technology recommendation."""
        job_title_lower = job_title.lower()
        
        # Base confidence
        confidence = 0.7
        
        # Boost if directly mentioned in job title
        if tech_keyword in job_title_lower:
            confidence += 0.2
        
        # Boost for common combinations
        if 'senior' in job_title_lower and tech_keyword in ['python', 'java', 'javascript']:
            confidence += 0.1
        
        if 'full stack' in job_title_lower and tech_keyword in ['javascript', 'python', 'java']:
            confidence += 0.1
        
        if 'devops' in job_title_lower and tech_keyword in ['aws', 'docker']:
            confidence += 0.15
        
        return min(confidence, 1.0)
    
    def _determine_focus_areas(self, job_title: str, recommendations: List[TechStackRecommendation]) -> List[str]:
        """Determine key focus areas for resume customization."""
        focus_areas = []
        job_title_lower = job_title.lower()
        
        # Role-based focus areas
        if 'senior' in job_title_lower:
            focus_areas.append('Leadership and mentoring experience')
            focus_areas.append('Complex problem-solving and architecture')
        
        if 'lead' in job_title_lower or 'manager' in job_title_lower:
            focus_areas.append('Team management and collaboration')
            focus_areas.append('Project planning and execution')
        
        if 'full stack' in job_title_lower:
            focus_areas.append('End-to-end development experience')
            focus_areas.append('Frontend and backend integration')
        
        if 'devops' in job_title_lower:
            focus_areas.append('CI/CD and deployment automation')
            focus_areas.append('Infrastructure and monitoring')
        
        # Technology-based focus areas
        tech_focuses = {
            'python': 'Data processing and backend development',
            'javascript': 'Frontend development and user experience',
            'aws': 'Cloud architecture and scalability',
            'docker': 'Containerization and microservices'
        }
        
        for rec in recommendations:
            if rec.tech_name.lower() in tech_focuses:
                focus_areas.append(tech_focuses[rec.tech_name.lower()])
        
        return list(set(focus_areas))  # Remove duplicates

class RequirementsBasedCustomization:
    """Handles resume customization based on specific job requirements."""
    
    def __init__(self):
        self.analyzer = RequirementsAnalyzer()
        self.requirements_manager = RequirementsManager()
    
    def generate_custom_tech_stack_input(self, requirement_id: str) -> str:
        """
        Generate tech stack input text optimized for a specific job requirement.
        
        Args:
            requirement_id: ID of the job requirement
            
        Returns:
            Formatted tech stack input text
        """
        plan = self.analyzer.analyze_job_requirement(requirement_id)
        if not plan:
            return ""
        
        tech_stack_lines = []
        
        for recommendation in plan.recommended_tech_stacks:
            if recommendation.confidence > 0.6:  # Only include high-confidence recommendations
                tech_name = recommendation.tech_name
                points = recommendation.suggested_points
                
                # Format as: "TechName: • point1 • point2 • point3"
                formatted_line = f"{tech_name}: " + " ".join(f"• {point}" for point in points)
                tech_stack_lines.append(formatted_line)
        
        return "\n".join(tech_stack_lines)
    
    def get_requirement_statistics(self) -> Dict[str, Any]:
        """Get statistics about requirements and their technology patterns."""
        requirements = self.requirements_manager.list_requirements()
        
        if not requirements:
            return {"message": "No requirements found"}
        
        stats = {
            "total_requirements": len(requirements),
            "by_status": {},
            "top_technologies": {},
            "top_clients": {},
            "recent_activity": []
        }
        
        # Analyze requirements
        for req in requirements:
            # Status distribution
            status = req.get('status', 'Unknown')
            stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Client distribution
            client = req.get('client', 'Unknown')
            stats['top_clients'][client] = stats['top_clients'].get(client, 0) + 1
            
            # Extract tech keywords for analysis
            tech_keywords = self.analyzer._extract_tech_keywords(req)
            for tech in tech_keywords:
                stats['top_technologies'][tech] = stats['top_technologies'].get(tech, 0) + 1
            
            # Recent activity (last 30 days)
            created_at = req.get('created_at', '')
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if (datetime.now() - created_date).days <= 30:
                        stats['recent_activity'].append({
                            'job_title': req.get('job_title', 'Unknown'),
                            'client': req.get('client', 'Unknown'),
                            'status': req.get('status', 'Unknown'),
                            'created_at': created_at
                        })
                except:
                    pass
        
        # Sort by frequency
        stats['top_technologies'] = dict(sorted(stats['top_technologies'].items(), 
                                               key=lambda x: x[1], reverse=True)[:10])
        stats['top_clients'] = dict(sorted(stats['top_clients'].items(), 
                                         key=lambda x: x[1], reverse=True)[:10])
        
        return stats

def render_requirements_analytics():
    """Render analytics dashboard for requirements."""
    st.subheader("📊 Requirements Analytics")
    
    customization = RequirementsBasedCustomization()
    stats = customization.get_requirement_statistics()
    
    if "message" in stats:
        st.info(stats["message"])
        return
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Requirements", stats["total_requirements"])
    
    with col2:
        active_count = sum(count for status, count in stats["by_status"].items() 
                          if status in ["Applied", "Submitted"])
        st.metric("Active Applications", active_count)
    
    with col3:
        recent_count = len(stats["recent_activity"])
        st.metric("Recent (30 days)", recent_count)
    
    with col4:
        tech_diversity = len(stats["top_technologies"])
        st.metric("Tech Diversity", tech_diversity)
    
    # Status distribution
    if stats["by_status"]:
        st.subheader("📈 Status Distribution")
        for status, count in stats["by_status"].items():
            percentage = (count / stats["total_requirements"]) * 100
            st.write(f"**{status}**: {count} ({percentage:.1f}%)")
    
    # Top technologies and clients
    col1, col2 = st.columns(2)
    
    with col1:
        if stats["top_technologies"]:
            st.subheader("🔧 Popular Technologies")
            for tech, count in stats["top_technologies"].items():
                st.write(f"• **{tech.title()}**: {count} requirements")
    
    with col2:
        if stats["top_clients"]:
            st.subheader("🏢 Top Clients")
            for client, count in stats["top_clients"].items():
                st.write(f"• **{client}**: {count} applications")

def render_smart_customization_panel():
    """Render smart customization panel based on requirements."""
    st.subheader("🎯 Smart Resume Customization")
    
    requirements_manager = RequirementsManager()
    requirements = requirements_manager.list_requirements()
    
    if not requirements:
        st.info("No requirements available. Create some job requirements first!")
        return
    
    # Select requirement for customization
    requirement_options = {}
    for req in requirements:
        display_name = f"{req.get('job_title', 'Untitled')} @ {req.get('client', 'Unknown')}"
        requirement_options[display_name] = req.get('id')
    
    selected_display = st.selectbox(
        "Select Job Requirement for Resume Customization:",
        list(requirement_options.keys())
    )
    
    if selected_display:
        selected_id = requirement_options[selected_display]
        
        # Generate customization plan
        customization = RequirementsBasedCustomization()
        plan = customization.analyzer.analyze_job_requirement(selected_id)
        
        if plan:
            st.markdown("---")
            st.markdown(f"### 📋 Customization Plan for {plan.job_title}")
            
            # Show recommendations
            if plan.recommended_tech_stacks:
                st.markdown("**🔧 Recommended Technology Focus:**")
                for rec in plan.recommended_tech_stacks:
                    confidence_color = "green" if rec.confidence > 0.8 else "orange" if rec.confidence > 0.6 else "red"
                    st.markdown(f"- **{rec.tech_name}** "
                              f"<span style='color:{confidence_color}'>({rec.confidence:.0%} confidence)</span>", 
                              unsafe_allow_html=True)
                    st.markdown(f"  *{rec.reasoning}*")
            
            # Show focus areas
            if plan.focus_areas:
                st.markdown("**🎯 Key Focus Areas:**")
                for area in plan.focus_areas:
                    st.markdown(f"- {area}")
            
            st.info(f"💡 This plan will add approximately **{plan.estimated_points} points** to your resume")
            
            # Generate optimized tech stack input
            if st.button("📝 Generate Optimized Tech Stack Input", key="generate_optimized"):
                optimized_input = customization.generate_custom_tech_stack_input(selected_id)
                
                if optimized_input:
                    st.markdown("**📋 Generated Tech Stack Input:**")
                    st.text_area(
                        "Copy this optimized input to the Resume Customizer:",
                        value=optimized_input,
                        height=200,
                        help="This input is optimized based on the selected job requirement"
                    )
                    
                    st.success("✅ Tech stack input generated! Copy and paste this into the Resume Customizer tab.")
                else:
                    st.warning("Could not generate optimized input for this requirement.")


