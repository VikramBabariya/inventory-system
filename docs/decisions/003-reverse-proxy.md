ADR 003: Adoption of Nginx as Reverse Proxy & Web Server

Status: Accepted Context: Our application consists of two distinct services (Frontend SPA and Backend API) running in separate containers. We need a single public entry point to route traffic effectively and handle security.

Decision: We chose Nginx.

Justification:

Unified Entry Point: Nginx allows us to expose only Port 80 (standard HTTP) to the user. It internally routes traffic to Port 3000 (Frontend) or Port 8000 (Backend) based on the URL path.

Static Content Performance: React produces static files (index.html, bundle.js). Nginx is optimized to serve these files with minimal CPU usage, freeing up our backend resources for logic.

Security/Isolation: It creates a "DMZ" (Demilitarized Zone). External users hit Nginx; they never touch the application containers directly.

Future Scale: Nginx can work as load balancer also.

Consequences:

We must maintain a custom nginx.conf file.

We add a slight hop in network latency (negligible).