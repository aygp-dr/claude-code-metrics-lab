;;; Claude Code Metrics Simulator in Guile Scheme
;;; 
;;; Generates realistic mock metrics using Brownian motion for educational
;;; telemetry development and testing. Provides Prometheus-compatible endpoint.

(use-modules (srfi srfi-1)   ; Lists
             (ice-9 format))

;;; Simple Brownian motion simulation without full web server
;;; (Simplified version due to Guile module complexity)

(define (random-normal)
  "Generate a normally distributed random number using Box-Muller transform"
  (let* ((u1 (/ (random 1000000) 1000000.0))  ; pseudo-uniform 0-1
         (u2 (/ (random 1000000) 1000000.0))  ; pseudo-uniform 0-1
         (z0 (* (sqrt (* -2 (log u1))) (cos (* 2 3.14159 u2)))))
    z0))

(define (brownian-motion current drift volatility dt)
  "Simple Brownian motion step"
  (+ current
     (* drift dt)
     (* volatility (sqrt dt) (random-normal))))

(define (bounded-value value bounds)
  "Apply bounds to a value"
  (max (car bounds) (min (cdr bounds) value)))

;;; Metrics state
(define *token-usage* 1000)
(define *session-duration* 300)
(define *cost* 0.50)

(define (update-metrics! dt)
  "Update all metrics using Brownian motion"
  (set! *token-usage* 
        (bounded-value (brownian-motion *token-usage* 0.1 5.0 dt) '(0 . 1000000)))
  (set! *session-duration*
        (bounded-value (brownian-motion *session-duration* 0.0 30.0 dt) '(10 . 7200)))
  (set! *cost*
        (bounded-value (brownian-motion *cost* 0.001 0.05 dt) '(0 . 1000))))

(define (format-prometheus-output)
  "Generate Prometheus format output"
  (let ((timestamp (inexact->exact (floor (* 1000 (+ (current-time) 1700000000))))))  ; Add epoch offset
    (format #f "# HELP otel_claude_code_token_usage_tokens_total Total tokens used (simulated)
# TYPE otel_claude_code_token_usage_tokens_total counter
otel_claude_code_token_usage_tokens_total{model=\"claude-3-sonnet\",project=\"simulation\"} ~a ~a

# HELP otel_claude_code_session_duration_seconds Session duration (simulated)
# TYPE otel_claude_code_session_duration_seconds gauge
otel_claude_code_session_duration_seconds{session_id=\"sim-001\",project=\"simulation\"} ~a ~a

# HELP otel_claude_code_cost_usd Cost in USD (simulated)
# TYPE otel_claude_code_cost_usd gauge
otel_claude_code_cost_usd{model=\"claude-3-sonnet\",project=\"simulation\"} ~a ~a
"
            (inexact->exact (floor *token-usage*)) timestamp
            *session-duration* timestamp
            *cost* timestamp)))

;;; Console-based simulation (simplified for compatibility)
(define (simulation-loop duration)
  "Run simulation for specified duration"
  (let ((start-time 0)  ; Simplified time tracking
        (update-interval 10))
    (format #t "Claude Code Metrics Simulator (Guile Scheme)~%")
    (format #t "Generating Brownian motion simulation...~%")
    (format #t "Duration: ~a seconds~%" duration)
    (format #t "Update interval: ~a seconds~%~%" update-interval)
    
    (set! *random-state* (seed->random-state (current-time)))
    
    (let loop ((elapsed 0))
      (when (< elapsed duration)
        (update-metrics! update-interval)
        (format #t "=== Time: ~a seconds ===~%" elapsed)
        (format #t "Token Usage: ~a~%" (inexact->exact (floor *token-usage*)))
        (format #t "Session Duration: ~a seconds~%" *session-duration*)
        (format #t "Cost: $~a~%~%" *cost*)
        
        ;; Output Prometheus format every 30 seconds
        (when (= (modulo elapsed 30) 0)
          (format #t "--- Prometheus Format ---~%")
          (display (format-prometheus-output))
          (format #t "--- End Prometheus Format ---~%~%"))
        
        ;; Simple sleep replacement (busy wait for compatibility)
        (let ((pause-end (+ (current-time) update-interval)))
          (let wait-loop ()
            (when (< (current-time) pause-end)
              (wait-loop))))
        
        (loop (+ elapsed update-interval))))))

;;; Main entry point
(define (main args)
  "Main function"
  (let ((duration (if (> (length args) 1)
                      (string->number (cadr args))
                      300)))  ; Default 5 minutes
    (simulation-loop duration)))

;;; Run if called directly
(when (and (> (length (command-line)) 0)
           (string-contains (car (command-line)) "claude-metrics-simulator.scm"))
  (main (command-line)))
