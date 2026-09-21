#!/usr/bin/env python3
"""
Claude API Synthesizer - Automated research synthesis using Claude
Manages API calls, token usage, and generates research improvements
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
import requests

class ClaudeAPISynthesizer:
    def __init__(self, api_key=None, budget_limit=50.0):
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        self.budget_limit = budget_limit
        self.cost_used = 0.0
        self.base_path = Path("/home/activeloguser/activelog")
        
        # API endpoints and pricing
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.input_cost_per_1k = 0.015   # $0.015 per 1K input tokens
        self.output_cost_per_1k = 0.075  # $0.075 per 1K output tokens
        
        # Setup logging
        self.log_path = self.base_path / "SYSTEM" / "LOGS" / "claude_api.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, message):
        """Log message with timestamp"""
        with open(self.log_path, 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {message}\n")
        print(f"{datetime.now().strftime('%H:%M:%S')}: {message}")
    
    def estimate_tokens(self, text):
        """Rough token estimation (4 chars = 1 token average)"""
        return len(text) // 4
    
    def calculate_cost(self, input_tokens, output_tokens):
        """Calculate API call cost"""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost
    
    def call_claude_api(self, prompt, max_tokens=2000, model="claude-3-5-sonnet-20241022"):
        """Make Claude API call with cost tracking"""
        
        if not self.api_key:
            self.log("ERROR: No Claude API key available")
            return None
        
        # Estimate input tokens and cost
        input_tokens = self.estimate_tokens(prompt)
        estimated_cost = self.calculate_cost(input_tokens, max_tokens)
        
        if self.cost_used + estimated_cost > self.budget_limit:
            self.log(f"Budget limit reached: ${self.cost_used:.2f} + ${estimated_cost:.2f} > ${self.budget_limit}")
            return None
        
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            self.log(f"Making Claude API call (est. cost: ${estimated_cost:.3f})")
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # Calculate actual cost based on usage
            usage = result.get('usage', {})
            actual_input_tokens = usage.get('input_tokens', input_tokens)
            actual_output_tokens = usage.get('output_tokens', max_tokens // 2)  # Conservative estimate
            actual_cost = self.calculate_cost(actual_input_tokens, actual_output_tokens)
            
            self.cost_used += actual_cost
            self.log(f"API call successful. Cost: ${actual_cost:.3f}, Total: ${self.cost_used:.2f}")
            
            return {
                "content": result['content'][0]['text'] if result.get('content') else "",
                "usage": {
                    "input_tokens": actual_input_tokens,
                    "output_tokens": actual_output_tokens,
                    "cost": actual_cost
                }
            }
        
        except Exception as e:
            self.log(f"Claude API call failed: {str(e)}")
            return None
    
    def synthesize_research_documents(self, file_paths, synthesis_type="cross_pollination"):
        """Synthesize multiple research documents"""
        
        # Read and combine documents
        combined_content = ""
        for file_path in file_paths[:5]:  # Limit to 5 files to manage token usage
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    combined_content += f"\n\n=== {Path(file_path).name} ===\n{content[:3000]}..."  # First 3K chars
            except Exception as e:
                self.log(f"Failed to read {file_path}: {e}")
        
        if not combined_content:
            return None
        
        # Create synthesis prompt
        prompt = f"""
        You are conducting advanced research synthesis across multiple documents from the SuperInstance Chronicles and AI research project.

        Documents to synthesize:
        {combined_content}

        Please provide a comprehensive synthesis focusing on:

        1. **Cross-Pollination Opportunities**: How concepts from different documents enhance each other
        2. **Breakthrough Insights**: Novel connections and implications not obvious in individual documents  
        3. **Practical Implementation**: Concrete next steps for applying these insights
        4. **Research Gaps**: Areas requiring further investigation
        5. **Integration Framework**: How these insights fit into the overall SuperInstance vision

        Synthesis Type: {synthesis_type}

        Provide a structured, actionable synthesis that advances both the creative and technical aspects of the project.
        Focus on insights that bridge academic rigor with creative vision.
        """
        
        response = self.call_claude_api(prompt, max_tokens=3000)
        
        if response:
            # Save synthesis
            synthesis_dir = self.base_path / "SYSTEM" / "CLAUDE_SYNTHESES"
            synthesis_dir.mkdir(parents=True, exist_ok=True)
            
            synthesis_file = synthesis_dir / f"synthesis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            synthesis_data = {
                "timestamp": datetime.now().isoformat(),
                "synthesis_type": synthesis_type,
                "input_files": [str(Path(f).name) for f in file_paths],
                "content": response["content"],
                "usage": response["usage"],
                "cost_total": self.cost_used
            }
            
            with open(synthesis_file, 'w') as f:
                json.dump(synthesis_data, f, indent=2)
            
            self.log(f"Synthesis saved: {synthesis_file}")
            return synthesis_data
        
        return None
    
    def improve_document_quality(self, file_path, improvement_focus="clarity_and_depth"):
        """Improve a specific document using Claude"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.log(f"Failed to read {file_path}: {e}")
            return None
        
        if len(content) > 12000:  # Truncate very long documents
            content = content[:12000] + "..."
        
        prompt = f"""
        You are improving the quality and depth of a research document from the SuperInstance Chronicles project.

        Current Document:
        {content}

        Improvement Focus: {improvement_focus}

        Please provide improvements in these areas:

        1. **Conceptual Clarity**: Enhance explanations of complex concepts
        2. **Technical Accuracy**: Ensure scientific and mathematical accuracy
        3. **Integration Opportunities**: Suggest connections to other project areas
        4. **Practical Applications**: Add concrete implementation suggestions
        5. **Educational Value**: Improve accessibility without sacrificing depth

        Provide specific suggestions for improvement, including:
        - Text additions or modifications
        - Structural improvements
        - Additional concepts to explore
        - Cross-references to other project components

        Focus on actionable improvements that advance the project's goals.
        """
        
        response = self.call_claude_api(prompt, max_tokens=2500)
        
        if response:
            # Save improvement suggestions
            improvements_dir = self.base_path / "SYSTEM" / "DOCUMENT_IMPROVEMENTS"
            improvements_dir.mkdir(parents=True, exist_ok=True)
            
            improvement_file = improvements_dir / f"improvement_{Path(file_path).stem}_{datetime.now().strftime('%H%M%S')}.json"
            
            improvement_data = {
                "timestamp": datetime.now().isoformat(),
                "source_file": str(file_path),
                "improvement_focus": improvement_focus,
                "suggestions": response["content"],
                "usage": response["usage"],
                "cost_total": self.cost_used
            }
            
            with open(improvement_file, 'w') as f:
                json.dump(improvement_data, f, indent=2)
            
            self.log(f"Improvement suggestions saved: {improvement_file}")
            return improvement_data
        
        return None
    
    def generate_implementation_roadmap(self, research_areas):
        """Generate implementation roadmap from research areas"""
        
        research_summary = ""
        for area in research_areas:
            research_summary += f"\n- {area['name']}: {area.get('description', 'Research area')}"
        
        prompt = f"""
        Based on the SuperInstance Chronicles research project, generate a comprehensive implementation roadmap.

        Research Areas:
        {research_summary}

        Please create a detailed roadmap covering:

        1. **Phase 1 (Immediate - 1-2 months)**:
           - Quick wins and foundational implementations
           - MVP features for SuperInstance platform
           - Essential research validation

        2. **Phase 2 (Short-term - 3-6 months)**:
           - Core system development
           - Educational content creation
           - Community engagement features

        3. **Phase 3 (Medium-term - 6-12 months)**:
           - Advanced AI integration
           - Full interactive experience
           - Commercial deployment preparation

        4. **Phase 4 (Long-term - 1-2 years)**:
           - Advanced research applications
           - Industry partnerships
           - Global impact initiatives

        For each phase, include:
        - Specific deliverables
        - Technical requirements
        - Success metrics
        - Resource estimates
        - Risk mitigation strategies

        Focus on creating a practical, achievable roadmap that bridges research innovation with commercial viability.
        """
        
        response = self.call_claude_api(prompt, max_tokens=3500)
        
        if response:
            # Save roadmap
            roadmap_file = self.base_path / "SYSTEM" / f"IMPLEMENTATION_ROADMAP_{datetime.now().strftime('%Y%m%d')}.md"
            
            with open(roadmap_file, 'w') as f:
                f.write(f"# SuperInstance Implementation Roadmap\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total API Cost: ${self.cost_used:.2f}\n\n")
                f.write(response["content"])
            
            self.log(f"Implementation roadmap saved: {roadmap_file}")
            return roadmap_file
        
        return None
    
    def get_cost_summary(self):
        """Get current cost usage summary"""
        return {
            "total_cost": self.cost_used,
            "budget_limit": self.budget_limit,
            "remaining_budget": self.budget_limit - self.cost_used,
            "percentage_used": (self.cost_used / self.budget_limit) * 100 if self.budget_limit > 0 else 0
        }

# Example usage and testing
if __name__ == "__main__":
    synthesizer = ClaudeAPISynthesizer(budget_limit=10.0)  # $10 test budget
    
    # Test with available files
    test_files = [
        "/home/activeloguser/activelog/MASTER_DISSERTATION/5_PAGE_REDACTED_DISSERTATION.md",
        "/home/activeloguser/activelog/CREATIVE_PROJECTS/SUPERINSTANCE_SERIES/tensor_narrative_structure.md"
    ]
    
    existing_files = [f for f in test_files if Path(f).exists()]
    
    if existing_files:
        print(f"Testing synthesis with {len(existing_files)} files...")
        result = synthesizer.synthesize_research_documents(existing_files)
        
        if result:
            print("Synthesis successful!")
            print(f"Cost: ${result['usage']['cost']:.3f}")
        else:
            print("Synthesis failed")
    
    # Print cost summary
    summary = synthesizer.get_cost_summary()
    print(f"\nCost Summary: ${summary['total_cost']:.2f} / ${summary['budget_limit']:.2f} ({summary['percentage_used']:.1f}%)")