"""
Alert Management System

Send alerts via email, Slack, or webhooks when signals trigger.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import requests
import json
from pathlib import Path


class AlertType(Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertChannel(Enum):
    """Alert delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    LOG = "log"


@dataclass
class Alert:
    """An alert message."""
    title: str
    message: str
    alert_type: AlertType
    timestamp: datetime
    metadata: Dict
    channels: List[AlertChannel]


class AlertManager:
    """Manage and send alerts."""

    def __init__(
        self,
        email_config: Optional[Dict] = None,
        slack_config: Optional[Dict] = None,
        webhook_config: Optional[Dict] = None
    ):
        """
        Initialize alert manager.

        Parameters
        ----------
        email_config : dict, optional
            Email configuration:
            - smtp_server: SMTP server address
            - smtp_port: SMTP port
            - username: Email username
            - password: Email password
            - from_address: Sender email
            - to_addresses: List of recipient emails
        slack_config : dict, optional
            Slack configuration:
            - webhook_url: Slack webhook URL
        webhook_config : dict, optional
            Generic webhook configuration:
            - url: Webhook URL
            - headers: Optional headers dict
        """
        self.email_config = email_config or {}
        self.slack_config = slack_config or {}
        self.webhook_config = webhook_config or {}

        # Alert history
        self.alert_history: List[Alert] = []

    def send_alert(self, alert: Alert):
        """
        Send an alert through configured channels.

        Parameters
        ----------
        alert : Alert
            Alert to send
        """
        self.alert_history.append(alert)

        for channel in alert.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    self._send_email(alert)
                elif channel == AlertChannel.SLACK:
                    self._send_slack(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook(alert)
                elif channel == AlertChannel.LOG:
                    self._log_alert(alert)
            except Exception as e:
                print(f"Error sending alert via {channel.value}: {e}")

    def _send_email(self, alert: Alert):
        """Send alert via email."""
        if not self.email_config:
            return

        msg = MIMEMultipart()
        msg['From'] = self.email_config.get('from_address', '')
        msg['To'] = ', '.join(self.email_config.get('to_addresses', []))
        msg['Subject'] = f"[{alert.alert_type.value}] {alert.title}"

        # Build HTML email body
        body = f"""
        <html>
        <body>
            <h2>{alert.title}</h2>
            <p><strong>Type:</strong> {alert.alert_type.value}</p>
            <p><strong>Time:</strong> {alert.timestamp}</p>
            <hr>
            <p>{alert.message}</p>
            <hr>
            <p><strong>Metadata:</strong></p>
            <pre>{json.dumps(alert.metadata, indent=2)}</pre>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # Send email
        with smtplib.SMTP(
            self.email_config['smtp_server'],
            self.email_config.get('smtp_port', 587)
        ) as server:
            server.starttls()
            server.login(
                self.email_config['username'],
                self.email_config['password']
            )
            server.send_message(msg)

    def _send_slack(self, alert: Alert):
        """Send alert via Slack."""
        if not self.slack_config or 'webhook_url' not in self.slack_config:
            return

        # Build Slack message
        color_map = {
            AlertType.INFO: "#36a64f",
            AlertType.WARNING: "#ff9900",
            AlertType.CRITICAL: "#ff0000"
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.alert_type, "#cccccc"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Type",
                            "value": alert.alert_type.value,
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True
                        }
                    ],
                    "footer": "Multi Asset Factor Dashboard",
                    "ts": int(alert.timestamp.timestamp())
                }
            ]
        }

        # Add metadata as fields
        for key, value in alert.metadata.items():
            payload["attachments"][0]["fields"].append({
                "title": key,
                "value": str(value),
                "short": True
            })

        response = requests.post(
            self.slack_config['webhook_url'],
            json=payload
        )
        response.raise_for_status()

    def _send_webhook(self, alert: Alert):
        """Send alert via generic webhook."""
        if not self.webhook_config or 'url' not in self.webhook_config:
            return

        payload = {
            "title": alert.title,
            "message": alert.message,
            "type": alert.alert_type.value,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata
        }

        headers = self.webhook_config.get('headers', {})
        headers.setdefault('Content-Type', 'application/json')

        response = requests.post(
            self.webhook_config['url'],
            json=payload,
            headers=headers
        )
        response.raise_for_status()

    def _log_alert(self, alert: Alert):
        """Log alert to file."""
        log_dir = Path("logs/alerts")
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"alerts_{datetime.now().strftime('%Y%m%d')}.log"

        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{alert.timestamp}] [{alert.alert_type.value}] {alert.title}\n")
            f.write(f"{alert.message}\n")
            f.write(f"Metadata: {json.dumps(alert.metadata, indent=2)}\n")

    def create_signal_alert(
        self,
        signal_data: Dict,
        channels: List[AlertChannel] = None
    ) -> Alert:
        """
        Create an alert from signal data.

        Parameters
        ----------
        signal_data : dict
            Signal information
        channels : list, optional
            Channels to send alert through

        Returns
        -------
        alert : Alert
        """
        if channels is None:
            channels = [AlertChannel.LOG]

        # Determine alert type based on signal confidence
        confidence = signal_data.get('confidence', 0.5)
        if confidence >= 0.8:
            alert_type = AlertType.CRITICAL
        elif confidence >= 0.6:
            alert_type = AlertType.WARNING
        else:
            alert_type = AlertType.INFO

        title = f"Trading Signal: {signal_data.get('signal', 'UNKNOWN')} - {signal_data.get('instrument', '')}"

        message = signal_data.get('reason', 'No reason provided')

        metadata = {
            k: v for k, v in signal_data.items()
            if k not in ['title', 'message', 'reason']
        }

        alert = Alert(
            title=title,
            message=message,
            alert_type=alert_type,
            timestamp=datetime.now(),
            metadata=metadata,
            channels=channels
        )

        return alert

    def create_regime_change_alert(
        self,
        old_regime: str,
        new_regime: str,
        asset_class: str,
        confidence: float,
        channels: List[AlertChannel] = None
    ) -> Alert:
        """Create an alert for regime changes."""
        if channels is None:
            channels = [AlertChannel.LOG]

        title = f"Regime Change: {asset_class}"
        message = f"Market regime changed from {old_regime} to {new_regime} (confidence: {confidence:.1%})"

        alert = Alert(
            title=title,
            message=message,
            alert_type=AlertType.WARNING,
            timestamp=datetime.now(),
            metadata={
                'asset_class': asset_class,
                'old_regime': old_regime,
                'new_regime': new_regime,
                'confidence': confidence
            },
            channels=channels
        )

        return alert

    def get_recent_alerts(
        self,
        hours: int = 24,
        alert_type: Optional[AlertType] = None
    ) -> List[Alert]:
        """Get recent alerts."""
        cutoff = datetime.now().timestamp() - (hours * 3600)

        alerts = [
            a for a in self.alert_history
            if a.timestamp.timestamp() >= cutoff
        ]

        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]

        return alerts
