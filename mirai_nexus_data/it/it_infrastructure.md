# IT Infrastructure Overview (Mirai Nexus)

- **Cloud Environment:**  
  - Primary: AWS (us-west-2)  
  - Secondary / Disaster Recovery: AWS (eu-west-1)  
  - Accounts configured with role-based access control and multi-factor authentication.

- **CI/CD Pipelines:**  
  - GitHub Actions used for mainline development, testing, and deployment.  
  - Automated testing includes unit, integration, and security scans.  
  - Deployments follow blue/green or canary strategies to minimize downtime.

- **Backups & Recovery:**  
  - Daily snapshots for production databases; weekly full backups stored in encrypted S3.  
  - Backup verification performed weekly.  
  - Disaster recovery procedures tested semi-annually.

- **Monitoring & Security:**  
  - CloudWatch and Datadog for real-time monitoring.  
  - Alerts for critical service disruptions and threshold breaches.  
  - Regular patching and vulnerability scans to ensure compliance and security.

- **Networking:**  
  - VPC segmentation for production, staging, and development environments.  
  - VPN access for remote employees with strict access policies.  

- **Documentation:**  
  - All infrastructure changes and SOPs documented in the internal Wiki.  
  - Runbooks maintained for critical incident response and recovery.