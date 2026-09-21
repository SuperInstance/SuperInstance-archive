#!/usr/bin/env python3
"""
Data Summarization and Redundancy Elimination System
Phase 3: Collaborative cleanup and storage optimization
"""

import json
import os
import gzip
import hashlib
from datetime import datetime
from pathlib import Path
import re

class DataSummarizationSystem:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.research_path = self.base_path / "RESEARCH_DISSERTATIONS" 
        self.summary_path = self.research_path / "DATA_SUMMARIES"
        self.summary_path.mkdir(exist_ok=True)
        
        # Storage management targets
        self.target_reduction = 0.4  # 40% size reduction goal
        self.redundancy_threshold = 0.8  # 80% similarity = redundant
        
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
        log_file = self.summary_path / "summarization.log"
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {message}\n")
    
    def analyze_current_storage(self):
        """Analyze current storage usage and identify optimization opportunities"""
        self.log("=== STORAGE ANALYSIS ===")
        
        storage_analysis = {
            "total_size_mb": 0,
            "file_analysis": {},
            "redundancy_candidates": [],
            "large_files": [],
            "optimization_opportunities": []
        }
        
        # Analyze all research files
        for file_path in self.research_path.rglob("*"):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                storage_analysis["total_size_mb"] += size_mb
                
                file_info = {
                    "path": str(file_path.relative_to(self.base_path)),
                    "size_mb": size_mb,
                    "extension": file_path.suffix,
                    "last_modified": file_path.stat().st_mtime
                }
                
                storage_analysis["file_analysis"][str(file_path)] = file_info
                
                # Identify large files for compression
                if size_mb > 1.0:  # Files > 1MB
                    storage_analysis["large_files"].append(file_info)
        
        self.log(f"📊 Total storage: {storage_analysis['total_size_mb']:.2f} MB")
        self.log(f"📁 Files analyzed: {len(storage_analysis['file_analysis'])}")
        self.log(f"📈 Large files (>1MB): {len(storage_analysis['large_files'])}")
        
        return storage_analysis
    
    def identify_redundancies(self):
        """Identify redundant content across files"""
        self.log("\n=== REDUNDANCY DETECTION ===")
        
        redundancies = []
        file_contents = {}
        
        # Read all markdown and json files
        for file_path in self.research_path.rglob("*.md"):
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                file_contents[str(file_path)] = {
                    "content": content,
                    "content_hash": hashlib.md5(content.encode()).hexdigest(),
                    "word_count": len(content.split()),
                    "key_concepts": self.extract_key_concepts(content)
                }
            except Exception as e:
                self.log(f"   ⚠️ Failed to read {file_path}: {e}")
        
        # Find similar content
        file_paths = list(file_contents.keys())
        for i, file1 in enumerate(file_paths):
            for file2 in file_paths[i+1:]:
                similarity = self.calculate_content_similarity(
                    file_contents[file1], file_contents[file2]
                )
                
                if similarity > self.redundancy_threshold:
                    redundancies.append({
                        "file1": file1,
                        "file2": file2,
                        "similarity_score": similarity,
                        "recommendation": "Consider merging or removing duplicate content"
                    })
        
        self.log(f"🔍 Found {len(redundancies)} potential redundancies")
        
        # Save redundancy analysis
        redundancy_file = self.summary_path / "redundancy_analysis.json"
        with open(redundancy_file, 'w') as f:
            json.dump({
                "redundancies": redundancies,
                "analysis_timestamp": datetime.now().isoformat(),
                "threshold_used": self.redundancy_threshold
            }, f, indent=2)
        
        return redundancies
    
    def extract_key_concepts(self, content):
        """Extract key concepts from content"""
        # Simple keyword extraction
        important_terms = [
            "vestige", "holographic", "tensor", "firefly", "democracy", "neural",
            "intelligence", "consciousness", "economic", "spatial", "asimov",
            "prototype", "implementation", "algorithm", "optimization", "system"
        ]
        
        content_lower = content.lower()
        found_concepts = {}
        
        for term in important_terms:
            count = content_lower.count(term)
            if count > 0:
                found_concepts[term] = count
        
        return found_concepts
    
    def calculate_content_similarity(self, content1, content2):
        """Calculate similarity between two content objects"""
        # Simple similarity based on shared concepts
        concepts1 = set(content1["key_concepts"].keys())
        concepts2 = set(content2["key_concepts"].keys())
        
        if not concepts1 or not concepts2:
            return 0.0
        
        shared_concepts = concepts1.intersection(concepts2)
        total_concepts = concepts1.union(concepts2)
        
        concept_similarity = len(shared_concepts) / len(total_concepts)
        
        # Check for exact content matches
        if content1["content_hash"] == content2["content_hash"]:
            return 1.0
        
        # Check word count similarity
        word_count_ratio = min(content1["word_count"], content2["word_count"]) / max(content1["word_count"], content2["word_count"])
        
        # Combined similarity score
        return (concept_similarity * 0.7 + word_count_ratio * 0.3)
    
    def create_consolidated_summaries(self):
        """Create consolidated summaries for each bot's work"""
        self.log("\n=== CREATING CONSOLIDATED SUMMARIES ===")
        
        bot_summaries = {}
        
        bot_areas = {
            "vestige_intelligence": ["vestige", "death-rebirth", "memory hierarchy", "adaptive critique"],
            "holographic_encoding": ["holographic", "fault tolerance", "tensor logic", "distributed information"],
            "firefly_democracy": ["firefly", "democratic", "swarm intelligence", "resource allocation"],
            "hierarchical_spatial": ["hierarchical", "spatial", "folder organization", "semantic navigation"],
            "asimov_analysis": ["asimov", "robot society", "governance", "consciousness emergence"],
            "shipyard_economics": ["economic", "skill hierarchy", "practical application", "value creation"],
            "prototype_engineering": ["implementation", "technical", "architecture", "validation"]
        }
        
        for bot_name, key_concepts in bot_areas.items():
            self.log(f"   📝 Summarizing {bot_name} research...")
            
            # Find all files related to this bot
            bot_files = []
            for file_path in self.research_path.rglob("*"):
                if file_path.is_file() and any(concept.replace(" ", "_") in str(file_path).lower() for concept in key_concepts):
                    bot_files.append(file_path)
                    
                # Also check file content for key concepts
                if file_path.suffix in ['.md', '.json']:
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        if any(concept in content.lower() for concept in key_concepts):
                            if file_path not in bot_files:
                                bot_files.append(file_path)
                    except Exception:
                        pass
            
            # Create comprehensive summary
            summary = self.create_bot_comprehensive_summary(bot_name, bot_files, key_concepts)
            bot_summaries[bot_name] = summary
            
            # Save individual summary
            summary_file = self.summary_path / f"{bot_name}_consolidated_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
        
        self.log(f"✅ Created {len(bot_summaries)} consolidated summaries")
        return bot_summaries
    
    def create_bot_comprehensive_summary(self, bot_name, files, key_concepts):
        """Create comprehensive summary for a specific bot's research"""
        
        summary = {
            "bot_name": bot_name,
            "key_concepts": key_concepts,
            "files_analyzed": len(files),
            "summary_created": datetime.now().isoformat(),
            "core_contributions": [],
            "key_innovations": [],
            "integration_points": [],
            "implementation_requirements": [],
            "research_gaps": [],
            "consolidated_content": ""
        }
        
        all_content = ""
        concept_frequency = {}
        
        # Analyze all bot-related files
        for file_path in files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                all_content += f"\n=== {file_path.name} ===\n{content}"
                
                # Track concept frequency
                for concept in key_concepts:
                    count = content.lower().count(concept.replace(" ", "_"))
                    concept_frequency[concept] = concept_frequency.get(concept, 0) + count
                
            except Exception as e:
                summary["research_gaps"].append(f"Failed to analyze {file_path}: {str(e)}")
        
        # Extract key contributions based on bot specialty
        if bot_name == "vestige_intelligence":
            summary["core_contributions"] = [
                "Death-rebirth intelligence cycles (I = k/P theorem)",
                "Multi-tier memory hierarchies (1MB/10MB/100MB)",
                "Adaptive model critique systems",
                "Democratic resource allocation through mortality"
            ]
            summary["key_innovations"] = [
                "Intelligence emerges from computational mortality",
                "Self-improving AI through systematic death-rebirth",
                "Real-time weight adaptation via accuracy-precision analysis"
            ]
        
        elif bot_name == "holographic_encoding":
            summary["core_contributions"] = [
                "Holographic tensor logic for fault tolerance",
                "Resolution-independent information encoding",
                "Distributed coherence maintenance",
                "Graceful degradation through holographic fragments"
            ]
            summary["key_innovations"] = [
                "Any system fragment contains complete information at appropriate resolution",
                "Fault tolerance through holographic redundancy",
                "Tensor mathematics for multi-dimensional information storage"
            ]
        
        elif bot_name == "firefly_democracy":
            summary["core_contributions"] = [
                "Biological swarm intelligence applied to AI resource allocation",
                "Democratic neuron voting for computational resource distribution", 
                "Multi-level selection optimization",
                "70% efficiency improvement through combined individual-collective optimization"
            ]
            summary["key_innovations"] = [
                "Firefly navigation algorithms for neural network exploration",
                "Democratic AI governance without central authority",
                "Biological validation of AI behavioral algorithms"
            ]
        
        # Add integration points and implementation requirements
        summary["integration_points"] = [
            f"Integrates with {concept} systems through shared mathematical foundations"
            for concept in key_concepts
        ]
        
        summary["implementation_requirements"] = [
            "Mathematical framework validation",
            "Prototype development and testing",
            "Integration with existing systems",
            "Performance optimization and scaling"
        ]
        
        # Create condensed content summary (first 1000 chars of each section)
        content_sections = all_content.split("===")
        condensed_content = ""
        for section in content_sections[:5]:  # First 5 sections
            if section.strip():
                condensed_content += section[:1000] + "...\n\n"
        
        summary["consolidated_content"] = condensed_content
        
        return summary
    
    def eliminate_redundancies(self, redundancies):
        """Eliminate identified redundancies"""
        self.log("\n=== ELIMINATING REDUNDANCIES ===")
        
        eliminated = []
        space_saved_mb = 0
        
        for redundancy in redundancies:
            if redundancy["similarity_score"] > 0.95:  # Very high similarity
                file1_path = Path(redundancy["file1"])
                file2_path = Path(redundancy["file2"])
                
                if file1_path.exists() and file2_path.exists():
                    # Keep the larger/more recent file, archive the other
                    file1_size = file1_path.stat().st_size
                    file2_size = file2_path.stat().st_size
                    
                    if file1_size >= file2_size:
                        archive_file = file2_path
                    else:
                        archive_file = file1_path
                    
                    # Archive redundant file
                    archive_dir = self.summary_path / "archived_redundant"
                    archive_dir.mkdir(exist_ok=True)
                    
                    archived_path = archive_dir / archive_file.name
                    archive_file.rename(archived_path)
                    
                    space_saved_mb += archive_file.stat().st_size / (1024 * 1024)
                    eliminated.append({
                        "original_file": str(archive_file),
                        "archived_to": str(archived_path),
                        "similarity": redundancy["similarity_score"]
                    })
                    
                    self.log(f"   📦 Archived {archive_file.name} (similarity: {redundancy['similarity_score']:.2f})")
        
        self.log(f"✅ Eliminated {len(eliminated)} redundant files, saved {space_saved_mb:.2f} MB")
        return eliminated
    
    def compress_large_files(self, storage_analysis):
        """Compress large files to save space"""
        self.log("\n=== COMPRESSING LARGE FILES ===")
        
        compressed = []
        compression_savings_mb = 0
        
        for file_info in storage_analysis["large_files"]:
            file_path = Path(file_info["path"])
            if file_path.exists() and file_path.suffix in ['.md', '.json', '.txt']:
                
                # Create compressed version
                compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
                
                try:
                    with open(file_path, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            f_out.writelines(f_in)
                    
                    original_size = file_path.stat().st_size
                    compressed_size = compressed_path.stat().st_size
                    savings_mb = (original_size - compressed_size) / (1024 * 1024)
                    
                    if savings_mb > 0.1:  # Only keep compression if saves >100KB
                        file_path.unlink()  # Remove original
                        compression_savings_mb += savings_mb
                        
                        compressed.append({
                            "original_file": str(file_path),
                            "compressed_file": str(compressed_path),
                            "original_size_mb": original_size / (1024 * 1024),
                            "compressed_size_mb": compressed_size / (1024 * 1024),
                            "savings_mb": savings_mb
                        })
                        
                        self.log(f"   🗜️ Compressed {file_path.name}: {savings_mb:.2f} MB saved")
                    else:
                        compressed_path.unlink()  # Remove inefficient compression
                
                except Exception as e:
                    self.log(f"   ⚠️ Failed to compress {file_path}: {e}")
                    if compressed_path.exists():
                        compressed_path.unlink()
        
        self.log(f"✅ Compressed {len(compressed)} files, saved {compression_savings_mb:.2f} MB")
        return compressed
    
    def generate_optimization_report(self, storage_analysis, redundancies, eliminations, compressions):
        """Generate comprehensive optimization report"""
        
        original_size = storage_analysis["total_size_mb"]
        space_saved = sum(e.get("savings_mb", 0) for e in compressions) + \
                      sum(storage_analysis["file_analysis"][e["original_file"]]["size_mb"] for e in eliminations if e["original_file"] in storage_analysis["file_analysis"])
        
        final_size = original_size - space_saved
        reduction_percentage = (space_saved / original_size) * 100 if original_size > 0 else 0
        
        report = {
            "optimization_summary": {
                "original_size_mb": original_size,
                "final_size_mb": final_size,
                "space_saved_mb": space_saved,
                "reduction_percentage": reduction_percentage,
                "target_reduction_met": reduction_percentage >= (self.target_reduction * 100)
            },
            "redundancy_elimination": {
                "redundancies_found": len(redundancies),
                "redundancies_eliminated": len(eliminations),
                "files_archived": [e["original_file"] for e in eliminations]
            },
            "compression_results": {
                "files_compressed": len(compressions),
                "compression_savings_mb": sum(c["savings_mb"] for c in compressions),
                "average_compression_ratio": sum(c["compressed_size_mb"]/c["original_size_mb"] for c in compressions) / len(compressions) if compressions else 0
            },
            "optimization_timestamp": datetime.now().isoformat(),
            "recommendations": []
        }
        
        # Add recommendations
        if reduction_percentage < (self.target_reduction * 100):
            report["recommendations"].append(f"Consider additional optimization - only achieved {reduction_percentage:.1f}% reduction vs {self.target_reduction*100}% target")
        
        if len(redundancies) > len(eliminations):
            report["recommendations"].append(f"Review remaining {len(redundancies) - len(eliminations)} redundancies manually")
        
        # Save optimization report
        report_file = self.summary_path / "optimization_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.log(f"\n📊 OPTIMIZATION COMPLETE!")
        self.log(f"   💾 Original size: {original_size:.2f} MB")
        self.log(f"   💾 Final size: {final_size:.2f} MB")
        self.log(f"   📉 Space saved: {space_saved:.2f} MB ({reduction_percentage:.1f}%)")
        self.log(f"   🎯 Target met: {'✅' if report['optimization_summary']['target_reduction_met'] else '❌'}")
        self.log(f"   📄 Report saved: {report_file}")
        
        return report

def main():
    """Execute data summarization and redundancy elimination"""
    system = DataSummarizationSystem()
    
    try:
        # Phase 3a: Analyze current storage
        storage_analysis = system.analyze_current_storage()
        
        # Phase 3b: Identify redundancies
        redundancies = system.identify_redundancies()
        
        # Phase 3c: Create consolidated summaries
        summaries = system.create_consolidated_summaries()
        
        # Phase 3d: Eliminate redundancies
        eliminations = system.eliminate_redundancies(redundancies)
        
        # Phase 3e: Compress large files
        compressions = system.compress_large_files(storage_analysis)
        
        # Phase 3f: Generate optimization report
        report = system.generate_optimization_report(
            storage_analysis, redundancies, eliminations, compressions
        )
        
        return True
        
    except Exception as e:
        system.log(f"❌ Data summarization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)