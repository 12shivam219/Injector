"""
Point distribution module for Resume Customizer.
Handles distribution of tech stack points across projects with improved error handling.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import random
from infrastructure.utilities.logger import get_logger

logger = get_logger()

@dataclass
class DistributionResult:
    """Data class to hold distribution results."""
    distribution: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    unused_points: List[Dict[str, Any]] = field(default_factory=list)
    all_points: List[Dict[str, Any]] = field(default_factory=list)


class PointDistributor:
    """Handles distribution of points across projects."""
    
    def distribute_points(self, projects: List[Dict], tech_stacks_data: Any) -> DistributionResult:
        """
        Distribute tech stack points across the top 3 projects using round-robin distribution.
        
        Args:
            projects: List of project dictionaries
            tech_stacks_data: Either a dictionary of tech stacks or tuple of (points, tech_names)
            
        Returns:
            DistributionResult object containing distribution results
        """
        result = DistributionResult()
        
        # Normalize tech stacks data
        tech_stacks = self._normalize_tech_stacks(tech_stacks_data)
        if not tech_stacks:
            return result
        
        # Limit to top 3 projects or all if less than 3
        top_projects = projects[:3] if len(projects) > 3 else projects
        if not top_projects:
            return result
        
        # Calculate distribution
        distribution = self._calculate_round_robin_distribution(tech_stacks, len(top_projects))
        
        # Prepare result
        for i, project in enumerate(top_projects):
            project_name = project.get('name', f'Project {i+1}')
            result.distribution[project_name] = distribution.get(i, [])
        
        # Track all points and unused points
        all_points = []
        for points in tech_stacks.values():
            all_points.extend(points)
        
        used_points = [point for points in distribution.values() for point in points]
        result.unused_points = [p for p in all_points if p not in used_points]
        result.all_points = all_points
        
        return result
    
    def _normalize_tech_stacks(self, tech_stacks_data: Any) -> Dict[str, List[Dict[str, Any]]]:
        """
        Normalize tech stacks data into a consistent format.
        
        Args:
            tech_stacks_data: Input tech stacks data in various formats
            
        Returns:
            Dictionary mapping tech stack names to lists of points
        """
        if not tech_stacks_data:
            return {}
            
        # Handle case where tech_stacks_data is a tuple of (points, tech_names)
        if isinstance(tech_stacks_data, tuple) and len(tech_stacks_data) == 2:
            points, tech_names = tech_stacks_data
            if isinstance(points, list) and isinstance(tech_names, list):
                return self._convert_points_format(points, tech_names)
        
        # Handle case where tech_stacks_data is already in the correct format
        if isinstance(tech_stacks_data, dict):
            return tech_stacks_data
            
        return {}
    
    def _convert_points_format(self, points: List[str], tech_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert points and tech names into the normalized format.
        
        Args:
            points: List of point strings
            tech_names: List of technology names
            
        Returns:
            Dictionary mapping tech stack names to lists of points
        """
        result = {}
        
        # Group points by technology
        for i, point in enumerate(points):
            # Find the technology this point belongs to
            for tech in tech_names:
                if tech.lower() in point.lower():
                    if tech not in result:
                        result[tech] = []
                    result[tech].append({
                        'text': point,
                        'tech': tech,
                        'original_index': i
                    })
                    break
        
        return result
    
    def _calculate_round_robin_distribution(
        self, 
        tech_stacks: Dict[str, List[Dict[str, Any]]], 
        num_projects: int
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        Calculate round-robin distribution of tech stack points across projects.
        
        Args:
            tech_stacks: Dictionary mapping tech names to lists of points
            num_projects: Number of projects to distribute points to
            
        Returns:
            Dictionary mapping project index to list of points
        """
        if num_projects <= 0:
            return {}
            
        # Initialize result structure
        distribution = {i: [] for i in range(num_projects)}
        
        # Flatten all points while keeping track of their tech
        all_points = []
        for tech, points in tech_stacks.items():
            for point in points:
                point['tech'] = tech
                all_points.append(point)
        
        # Shuffle to ensure random distribution within tech stacks
        random.shuffle(all_points)
        
        # Distribute points in round-robin fashion
        for i, point in enumerate(all_points):
            project_idx = i % num_projects
            distribution[project_idx].append(point)
        
        return distribution


