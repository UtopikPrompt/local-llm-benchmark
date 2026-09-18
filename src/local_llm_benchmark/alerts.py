"""Prometheus alerting manager.

This module provides alert rule management and monitoring capabilities
using Prometheus alerting framework.

Usage:
    >>> from prometheus_client import CollectorRegistry
    >>> from alerts import AlertManager
    >>> registry = CollectorRegistry()
    >>> alert_manager = AlertManager(registry)
    >>> alert_manager.register_alert("high_error_rate", "AlertRule(...)")
"""

from prometheus_client import CollectorRegistry, Alertmanager
from typing import Callable, Optional
from dataclasses import dataclass, field
import json


@dataclass
class AlertRule:
    """Represents a Prometheus alert rule.
    
    Attributes:
        name: Alert rule name
        expr: Alert expression (Prometheus query)
        for: How long to wait before firing (e.g., "5m")
        labels: Labels to apply to the alert
        annotations: Human-readable annotations
    """
    name: str
    expr: str
    for: str = "5m"
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)
    
    def to_yaml(self) -> str:
        """Convert to YAML format.
        
        Returns:
            YAML string representation
        """
        yaml_content = f"""- alert: {self.name}
    expr: {self.expr}
    for: {self.for}
    labels:
"""
        for key, value in self.labels.items():
            yaml_content += f"      {key}: \"{value}\"\n"
        yaml_content += f"    annotations:\n"
        for key, value in self.annotations.items():
            yaml_content += f"      {key}: \"{value}\"\n"
        yaml_content += ""
        return yaml_content


class AlertManager:
    """Prometheus alerting manager.
    
    Manages Prometheus alert rules and provides methods for
    creating, registering, and querying alerts.
    
    Attributes:
        registry: Prometheus collector registry
        alert_rules: Registered alert rules
    """
    
    def __init__(self, registry: CollectorRegistry):
        """Initialize the alert manager.
        
        Args:
            registry: Prometheus CollectorRegistry instance
        """
        self.registry = registry
        self.alert_rules: list[AlertRule] = []
    
    def register_alert(self, name: str, rule: str) -> AlertRule:
        """Register an alert rule.
        
        Args:
            name: Alert rule name
            rule: Alert rule definition
            
        Returns:
            Registered AlertRule instance
            
        Example:
            >>> alert_manager = AlertManager(registry)
            >>> alert_manager.register_alert(
            ...     "high_error_rate",
            ...     """
            alerting_rules:
            - alert: HighErrorRate
              expr: rate(http_requests_errors_total[5m]) > 0.05
              for: 5m
              labels:
                severity: warning
              annotations:
                summary: "High error rate detected"
                description: "Error rate exceeds 5% over the last 5 minutes"
            """
        )
        """
        # Parse the rule YAML
        alert_rule = AlertRule.from_yaml(rule)
        self.alert_rules.append(alert_rule)
        return alert_rule
    
    def register_alert_from_dict(self, name: str, rule_dict: dict) -> AlertRule:
        """Register an alert rule from dictionary.
        
        Args:
            name: Alert rule name
            rule_dict: Dictionary representation of the alert rule
            
        Returns:
            Registered AlertRule instance
        """
        alert_rule = AlertRule(
            name=rule_dict.get('name', name),
            expr=rule_dict.get('expr', ''),
            for=rule_dict.get('for', '5m'),
            labels=rule_dict.get('labels', {}),
            annotations=rule_dict.get('annotations', {})
        )
        self.alert_rules.append(alert_rule)
        return alert_rule
    
    def get_alerts(self) -> list:
        """Get current alerts.
        
        Fetches alerts from Prometheus and returns them as a list.
        
        Returns:
            List of alert dictionaries
        """
        try:
            # Fetch alerts from Prometheus
            alerts_response = self.registry._fetch_alerts()
            return alerts_response
        except Exception as e:
            # Return empty list if Prometheus is not available
            print(f"Warning: Could not fetch alerts from Prometheus: {e}")
            return []
    
    def get_alert_by_name(self, name: str) -> Optional[AlertRule]:
        """Get a specific alert rule by name.
        
        Args:
            name: Alert rule name
            
        Returns:
            AlertRule instance or None
        """
        for rule in self.alert_rules:
            if rule.name == name:
                return rule
        return None
    
    def get_alerts_summary(self) -> str:
        """Get a summary of all registered alerts.
        
        Returns:
            Human-readable summary string
        """
        lines = [
            "Alert Rules Summary",
            "=" * 40,
            f"Total Rules: {len(self.alert_rules)}",
            ""
        ]
        
        for rule in self.alert_rules:
            lines.append(f"  {rule.name}:")
            lines.append(f"    Expression: {rule.expr}")
            lines.append(f"    Duration: {rule.for}")
            lines.append(f"    Labels: {rule.labels}")
            lines.append(f"    Annotations: {rule.annotations}")
            lines.append("")
        
        return "\n".join(lines)
    
    def export_rules_yaml(self) -> str:
        """Export all alert rules as YAML.
        
        Returns:
            YAML string containing all alert rules
        """
        return "\n".join(rule.to_yaml() for rule in self.alert_rules)
    
    def load_rules_yaml(self, yaml_content: str) -> int:
        """Load alert rules from YAML content.
        
        Args:
            yaml_content: YAML string containing alert rules
            
        Returns:
            Number of rules loaded
        """
        rules_loaded = 0
        for line in yaml_content.split('\n'):
            if line.startswith('- alert:'):
                # Parse alert rule from YAML
                alert_name = line.split('- alert:')[1].strip()
                # Extract full rule block (simplified parsing)
                rule_dict = self._parse_alert_rule(line)
                if rule_dict:
                    self.register_alert_from_dict(alert_name, rule_dict)
                    rules_loaded += 1
        return rules_loaded
    
    def _parse_alert_rule(self, line: str) -> Optional[dict]:
        """Parse a single alert rule from YAML line.
        
        Args:
            line: YAML line starting with '- alert: name'
            
        Returns:
            Dictionary representation of the alert rule
        """
        # This is a simplified parser - for production use a proper YAML library
        try:
            import yaml
            content = line.strip()
            # Extract alert name and rule block
            if '- alert:' in content:
                parts = content.split('- alert:')
                name = parts[1].strip().strip('"').strip("'")
                # Return minimal rule structure
                return {'name': name}
        except Exception:
            pass
        return None
    
    def delete_alert(self, name: str) -> bool:
        """Delete an alert rule.
        
        Args:
            name: Alert rule name
            
        Returns:
            True if alert was deleted, False otherwise
        """
        for i, rule in enumerate(self.alert_rules):
            if rule.name == name:
                del self.alert_rules[i]
                return True
        return False
    
    def list_alerts(self) -> list[str]:
        """List all registered alert names.
        
        Returns:
            List of alert names
        """
        return [rule.name for rule in self.alert_rules]
    
    def get_rules_json(self) -> str:
        """Export all alert rules as JSON.
        
        Returns:
            JSON string containing all alert rules
        """
        return json.dumps([rule.to_dict() for rule in self.alert_rules], indent=2)
    
    def to_dict(self) -> dict:
        """Convert alert manager to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            'registry': str(self.registry),
            'alert_rules': [rule.to_dict() for rule in self.alert_rules],
            'alert_count': len(self.alert_rules)
        }


def create_default_alerts(registry: CollectorRegistry) -> AlertManager:
    """Create alert manager with default alert rules.
    
    Args:
        registry: Prometheus CollectorRegistry
        
    Returns:
        Configured AlertManager with default rules
    """
    alert_manager = AlertManager(registry)
    
    # Default alert rules
    default_rules = [
        {
            'name': 'HighErrorRate',
            'expr': 'rate(http_requests_errors_total[5m]) > 0.05',
            'for': '5m',
            'labels': {'severity': 'warning'},
            'annotations': {
                'summary': 'High error rate detected',
                'description': 'Error rate exceeds 5% over the last 5 minutes'
            }
        },
        {
            'name': 'HighLatency',
            'expr': 'histogram_quantile(0.99, rate(request_latency_seconds_bucket[5m])) > 10',
            'for': '2m',
            'labels': {'severity': 'warning'},
            'annotations': {
                'summary': 'High latency detected',
                'description': '99th percentile latency exceeds 10 seconds'
            }
        },
        {
            'name': 'HighMemoryUsage',
            'expr': 'memory_usage_bytes > 85767001600',  # 85GB
            'for': '5m',
            'labels': {'severity': 'critical'},
            'annotations': {
                'summary': 'High memory usage',
                'description': 'Memory usage exceeds 85GB'
            }
        },
        {
            'name': 'HighCPUTotal',
            'expr': 'sum(rate(cpu_total[5m])) > 0.8',
            'for': '5m',
            'labels': {'severity': 'warning'},
            'annotations': {
                'summary': 'High CPU usage',
                'description': 'Total CPU usage exceeds 80%'
            }
        }
    ]
    
    for rule in default_rules:
        alert_manager.register_alert_from_dict(rule['name'], rule)
    
    return alert_manager


if __name__ == "__main__":
    # Demo
    from prometheus_client import CollectorRegistry
    
    registry = CollectorRegistry()
    alert_manager = create_default_alerts(registry)
    
    print(alert_manager.get_alerts_summary())
    print("\n" + "=" * 40)
    print("Exported YAML:")
    print(alert_manager.export_rules_yaml())
