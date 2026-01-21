#!/usr/bin/env python3
"""
Comprehensive analyzer
Integrates toxicity analysis and topic diversity analysis
"""

import json
from datetime import datetime
import logging

from analyzers.toxicity_analyzer import ToxicityAnalyzer
from analyzers.topic_diversity_analyzer import TopicDiversityAnalyzer
# from analyzers.sentiment_analyzer import SentimentAnalyzer  # Temporarily disabled, not needed
try:
    from argument_quality_analyzer.aqs_analyzer import ComprehensiveArgumentEvaluator
    ARGUMENT_EVALUATOR_AVAILABLE = True
except ImportError:
    ARGUMENT_EVALUATOR_AVAILABLE = False
    logger.warning("Argument quality evaluator unavailable; skipping argument reasonableness analysis")
from keys import PERSPECTIVE_API_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveAnalyzer:
    """Comprehensive analyzer, integrates multiple analysis modules"""
    
    def __init__(self, api_key: str, language: str = 'english', enable_argument_evaluation: bool = True):
        """
        Initialize comprehensive analyzer

        Args:
            api_key: Perspective API key
            language: Language for topic analysis ('chinese' or 'english')
            enable_argument_evaluation: Whether to enable argument reasonableness evaluation
        """
        self.api_key = api_key
        self.language = language
        self.enable_argument_evaluation = enable_argument_evaluation and ARGUMENT_EVALUATOR_AVAILABLE
        
        # Initialize analyzers
        self.toxicity_analyzer = ToxicityAnalyzer(self.api_key)
        self.topic_analyzer = TopicDiversityAnalyzer(language=self.language)
        # self.sentiment_analyzer = SentimentAnalyzer()  # Temporarily disabled, not needed
        
        # Initialize argument quality evaluator (if available)
        if self.enable_argument_evaluation:
            try:
                self.argument_evaluator = ComprehensiveArgumentEvaluator()
                logger.info("✅ Argument reasonableness evaluator enabled")
            except Exception as e:
                logger.warning(f"⚠️ Argument reasonableness evaluator init failed: {e}")
                self.enable_argument_evaluation = False
        else:
            self.argument_evaluator = None
    
    def analyze_discussion(self, documents: list, discussion_id: str = "default_discussion") -> dict:
        """
        Perform comprehensive analysis on a document set
        
        Args:
            documents: Document/comment list
            discussion_id: Unique discussion identifier
            
        Returns:
            Comprehensive report with all analysis results
        """
        logger.info(f"---Starting comprehensive analysis for '{discussion_id}'---")
        
        # Initialize report
        comprehensive_report = {
            'discussion_id': discussion_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'total_documents': len(documents),
            'reports': {}
        }
        
        # 1. Toxicity and incivility analysis
        try:
            logger.info("1/2: Running toxicity analysis...")
            toxicity_report = self.toxicity_analyzer.analyze_discussion_thread(documents)
            comprehensive_report['reports']['toxicity_analysis'] = toxicity_report
            logger.info("✅ Toxicity analysis completed")
        except Exception as e:
            logger.error(f"❌ Toxicity analysis failed: {e}")
            comprehensive_report['reports']['toxicity_analysis'] = {'error': str(e)}
            
        # 2. Sentiment analysis - temporarily skipped, not needed
        # try:
        #     logger.info("2/3: Running sentiment analysis...")
        #     sentiment_report = self.sentiment_analyzer.analyze(documents)
        #     comprehensive_report['reports']['sentiment_analysis'] = sentiment_report
        #     logger.info("✅ Sentiment analysis completed")
        # except Exception as e:
        #     logger.error(f"❌ Sentiment analysis failed: {e}")
        #     comprehensive_report['reports']['sentiment_analysis'] = {'error': str(e)}

        # 3. Topic diversity and entropy analysis
        try:
            logger.info("3/4: Running topic diversity analysis...")
            topic_metrics = self.topic_analyzer.analyze_topic_diversity(documents)
            topic_report = {
                'metrics': topic_metrics.to_dict(),
                'topic_details': self.topic_analyzer.get_topic_details()
            }
            comprehensive_report['reports']['topic_diversity_analysis'] = topic_report
            logger.info("✅ Topic diversity analysis completed")
        except Exception as e:
            logger.error(f"❌ Topic diversity analysis failed: {e}")
            comprehensive_report['reports']['topic_diversity_analysis'] = {'error': str(e)}
        
        # 4. Argument reasonableness analysis (if enabled)
        if self.enable_argument_evaluation:
            try:
                logger.info("4/4: Running argument reasonableness analysis...")
                argument_results = self.argument_evaluator.batch_evaluate(documents)
                
                # Calculate argument quality statistics
                if argument_results:
                    overall_scores = [r['overall_reasonableness_score'] for r in argument_results]
                    aqs_scores = [r['detailed_scores']['argument_quality_score'] for r in argument_results]
                    logic_scores = [r['detailed_scores']['logical_soundness_score'] for r in argument_results]
                    evidence_scores = [r['detailed_scores']['evidence_usage_score'] for r in argument_results]
                    
                    # Logical fallacy statistics
                    total_fallacies = 0
                    fallacy_distribution = {}
                    for result in argument_results:
                        for fallacy_type, matches in result['detected_fallacies'].items():
                            total_fallacies += len(matches)
                            fallacy_distribution[fallacy_type] = fallacy_distribution.get(fallacy_type, 0) + len(matches)
                    
                    argument_report = {
                        'summary_statistics': {
                            'total_arguments': len(argument_results),
                            'average_overall_score': sum(overall_scores) / len(overall_scores),
                            'average_aqs_score': sum(aqs_scores) / len(aqs_scores),
                            'average_logic_score': sum(logic_scores) / len(logic_scores),
                            'average_evidence_score': sum(evidence_scores) / len(evidence_scores),
                            'total_fallacies_detected': total_fallacies,
                            'fallacy_rate': total_fallacies / len(argument_results) if argument_results else 0,
                            'fallacy_distribution': fallacy_distribution
                        },
                        'score_distribution': {
                            'excellent_arguments': len([s for s in overall_scores if s >= 8.5]),
                            'good_arguments': len([s for s in overall_scores if 7.0 <= s < 8.5]),
                            'moderate_arguments': len([s for s in overall_scores if 5.5 <= s < 7.0]),
                            'poor_arguments': len([s for s in overall_scores if 4.0 <= s < 5.5]),
                            'very_poor_arguments': len([s for s in overall_scores if s < 4.0])
                        },
                        'detailed_results': argument_results[:10] if len(argument_results) > 10 else argument_results  # Limit detail count
                    }
                    comprehensive_report['reports']['argument_reasonableness_analysis'] = argument_report
                    logger.info("✅ Argument reasonableness analysis completed")
                else:
                    logger.warning("⚠️ No valid argument results")
                    comprehensive_report['reports']['argument_reasonableness_analysis'] = {'error': 'No valid arguments to analyze'}
                    
            except Exception as e:
                logger.error(f"❌ Argument reasonableness analysis failed: {e}")
                comprehensive_report['reports']['argument_reasonableness_analysis'] = {'error': str(e)}
        else:
            logger.info("Skipping argument reasonableness analysis (disabled or unavailable)")
        
        # Generate summary metrics
        comprehensive_report['summary'] = self._generate_summary(comprehensive_report)
        
        logger.info("---Comprehensive analysis completed---")
        return comprehensive_report

    def _generate_summary(self, report: dict) -> dict:
        """Extract core metrics from analyzer reports and generate summary"""
        summary = {}
        
        # Initialize metrics
        sentiment_variance = 0.0
        toxicity_rate = 0.0

        # Extract toxicity summary
        toxicity_report = report['reports'].get('toxicity_analysis', {})
        if 'summary' in toxicity_report:
            summary['health_score'] = toxicity_report['summary'].get('health_score')
            summary['polarization_level'] = toxicity_report['summary'].get('polarization_level')
            summary['average_toxicity'] = toxicity_report['polarization_metrics'].get('average_toxicity')
            # Use high toxicity ratio as toxicity rate
            toxicity_rate = toxicity_report['polarization_metrics'].get('high_toxicity_percentage', 0.0) / 100.0

        # Extract sentiment summary
        sentiment_report = report['reports'].get('sentiment_analysis', {})
        if 'sentiment_variance' in sentiment_report:
            summary['sentiment_variance'] = sentiment_report.get('sentiment_variance')
            sentiment_variance = summary['sentiment_variance']

        # Extract topic diversity summary
        topic_report = report['reports'].get('topic_diversity_analysis', {})
        if 'metrics' in topic_report:
            summary['shannon_entropy'] = topic_report['metrics'].get('shannon_entropy')
            summary['num_topics'] = topic_report['metrics'].get('num_topics')
            summary['diversity_level'] = topic_report['metrics'].get('diversity_level')

        # Extract argument reasonableness summary
        argument_report = report['reports'].get('argument_reasonableness_analysis', {})
        if 'summary_statistics' in argument_report:
            stats = argument_report['summary_statistics']
            summary['average_argument_quality'] = stats.get('average_overall_score')
            summary['average_aqs_score'] = stats.get('average_aqs_score')
            summary['average_logic_score'] = stats.get('average_logic_score')
            summary['average_evidence_score'] = stats.get('average_evidence_score')
            summary['fallacy_rate'] = stats.get('fallacy_rate')
            summary['total_fallacies'] = stats.get('total_fallacies_detected')
            
            # Argument quality distribution
            dist = argument_report.get('score_distribution', {})
            total_args = stats.get('total_arguments', 1)
            summary['high_quality_argument_ratio'] = (dist.get('excellent_arguments', 0) + dist.get('good_arguments', 0)) / total_args
            summary['low_quality_argument_ratio'] = (dist.get('poor_arguments', 0) + dist.get('very_poor_arguments', 0)) / total_args

        # Calculate final emotional polarization score
        # Assume weights: sentiment variance 60%, toxicity rate 40%
        # Normalize sentiment variance to 0-1
        normalized_variance = min(sentiment_variance, 1.0)
        summary['emotional_polarization_score'] = (normalized_variance * 0.6) + (toxicity_rate * 0.4)

        # Calculate overall discussion quality score
        # Based on multiple dimensions: argument quality, toxicity, topic diversity, emotional polarization
        quality_components = []
        
        # Argument quality contribution (0-10 scale, weight: 30%)
        if 'average_argument_quality' in summary:
            quality_components.append(summary['average_argument_quality'] * 0.3)
        
        # Health contribution (reverse toxicity, weight: 25%)
        if 'health_score' in summary and summary['health_score'] is not None:
            quality_components.append(summary['health_score'] * 0.25)
        
        # Topic diversity contribution (normalized entropy, weight: 20%)
        if 'shannon_entropy' in summary and summary['shannon_entropy'] is not None:
            normalized_entropy = min(summary['shannon_entropy'] / 3.0, 1.0) * 10  # normalize to 0-10
            quality_components.append(normalized_entropy * 0.2)
        
        # Low polarization contribution (reverse polarization, weight: 25%)
        if summary['emotional_polarization_score'] is not None:
            low_polarization_score = (1.0 - summary['emotional_polarization_score']) * 10  # invert and scale to 0-10
            quality_components.append(low_polarization_score * 0.25)
        
        if quality_components:
            summary['overall_discussion_quality'] = sum(quality_components)
        else:
            summary['overall_discussion_quality'] = None

        return summary

    def export_report(self, report: dict, file_path: str = None) -> str:
        """Export comprehensive report to JSON file"""
        if not file_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            discussion_id = report.get('discussion_id', 'report')
            file_path = f"comprehensive_analysis_{discussion_id}_{timestamp}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 Comprehensive report exported to: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ Report export failed: {e}")
            return ""
