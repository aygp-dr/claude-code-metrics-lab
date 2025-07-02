#!/usr/bin/env bash
# TCS (Trailer Consistency Score) Report Generator
# Analyzes Git trailer attribution compliance and generates a detailed report

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(dirname "$0")"
REPO_ROOT="$(git rev-parse --show-toplevel)"
REPORTS_DIR="${REPO_ROOT}/reports"
COMMIT_COUNT=50 # Number of recent commits to analyze

# Create output directory if it doesn't exist
mkdir -p "${REPORTS_DIR}"

echo -e "${BLUE}Generating TCS Report...${NC}"

# Create temporary file to store recent commit hashes
TMP_COMMITS="/tmp/recent_commits.txt"
git log -n ${COMMIT_COUNT} --pretty=format:"%h" >"${TMP_COMMITS}"
TOTAL_COMMITS=$(cat "${TMP_COMMITS}" | wc -l | tr -d ' ')

# Check required trailers in recent commits
echo -e "${BLUE}Analyzing trailer compliance in the ${COMMIT_COUNT} most recent commits...${NC}"

# Define trailers to check
TRAILERS=("Driving-Agent" "LLM-Agent" "LLM-Model" "Reviewed-by" "Session-id")

# Initialize arrays for report data
declare -A trailer_counts
declare -A trailer_percentages
declare -A trailer_colors
declare -A trailer_missing

# Initialize report file
REPORT_FILE="${REPORTS_DIR}/tcs_report.md"
echo "# Trailer Consistency Score (TCS) Report" >"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"
echo "Generated on $(date)" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"
echo "## Summary" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"

# Initialize JSON report file
JSON_FILE="${REPORTS_DIR}/tcs.json"
echo '{' >"${JSON_FILE}"
echo '  "generated_at": "'"$(date -u +"%Y-%m-%dT%H:%M:%SZ")"'",' >>"${JSON_FILE}"
echo '  "commit_count": '"${TOTAL_COMMITS}"',' >>"${JSON_FILE}"
echo '  "trailers": {' >>"${JSON_FILE}"

# Generate data for each trailer
for trailer in "${TRAILERS[@]}"; do
  echo -e "${BLUE}Checking ${trailer} compliance...${NC}"

  # Count commits with this trailer
  trailer_counts[${trailer}]=0
  trailer_missing[${trailer}]=""

  while read -r sha; do
    if git show ${sha} --format="%b" | grep -q "${trailer}:"; then
      trailer_counts[${trailer}]=$((trailer_counts[${trailer}] + 1))
    else
      # Record missing trailer in commit
      short_commit=$(git show ${sha} --format="%h %s" | head -n1)
      trailer_missing[${trailer}]+="- ${short_commit}\n"
    fi
  done <"${TMP_COMMITS}"

  # Calculate percentage
  trailer_percentages[${trailer}]=$(echo "scale=1; ${trailer_counts[${trailer}]} * 100 / ${TOTAL_COMMITS}" | bc)

  # Determine color based on percentage
  if (($(echo "${trailer_percentages[${trailer}]} >= 90" | bc -l))); then
    trailer_colors[${trailer}]="brightgreen"
  elif (($(echo "${trailer_percentages[${trailer}]} >= 75" | bc -l))); then
    trailer_colors[${trailer}]="green"
  elif (($(echo "${trailer_percentages[${trailer}]} >= 50" | bc -l))); then
    trailer_colors[${trailer}]="yellow"
  else
    trailer_colors[${trailer}]="red"
  fi

  echo -e "${GREEN}${trailer}: ${trailer_percentages[${trailer}]}% (${trailer_counts[${trailer}]}/${TOTAL_COMMITS} commits) ${NC}"

  # Add to JSON
  echo '    "'"${trailer}"'": {' >>"${JSON_FILE}"
  echo '      "count": '"${trailer_counts[${trailer}]}"',' >>"${JSON_FILE}"
  echo '      "percentage": '"${trailer_percentages[${trailer}]}"',' >>"${JSON_FILE}"
  echo '      "color": "'"${trailer_colors[${trailer}]}"'"' >>"${JSON_FILE}"

  # Add comma if not last trailer
  if [[ "${trailer}" != "${TRAILERS[-1]}" ]]; then
    echo '    },' >>"${JSON_FILE}"
  else
    echo '    }' >>"${JSON_FILE}"
  fi
done

# Calculate overall TCS
TOTAL_PRESENT=0
for trailer in "${TRAILERS[@]}"; do
  TOTAL_PRESENT=$((TOTAL_PRESENT + trailer_counts[${trailer}]))
done

# Calculate TCS
TOTAL_POSSIBLE=$((TOTAL_COMMITS * ${#TRAILERS[@]}))
TCS=$(echo "scale=1; ${TOTAL_PRESENT} * 100 / ${TOTAL_POSSIBLE}" | bc)

# Determine color based on TCS
if (($(echo "${TCS} >= 90" | bc -l))); then
  TCS_COLOR="brightgreen"
elif (($(echo "${TCS} >= 75" | bc -l))); then
  TCS_COLOR="green"
elif (($(echo "${TCS} >= 50" | bc -l))); then
  TCS_COLOR="yellow"
else
  TCS_COLOR="red"
fi

echo -e "${GREEN}Overall TCS: ${TCS}% (${TOTAL_PRESENT}/${TOTAL_POSSIBLE} possible trailers) ${NC}"

# Finish JSON
echo '  },' >>"${JSON_FILE}"
echo '  "overall": {' >>"${JSON_FILE}"
echo '    "tcs": '"${TCS}"',' >>"${JSON_FILE}"
echo '    "present": '"${TOTAL_PRESENT}"',' >>"${JSON_FILE}"
echo '    "possible": '"${TOTAL_POSSIBLE}"',' >>"${JSON_FILE}"
echo '    "color": "'"${TCS_COLOR}"'"' >>"${JSON_FILE}"
echo '  }' >>"${JSON_FILE}"
echo '}' >>"${JSON_FILE}"

# Add badges to report
echo "[![TCS Badge](../static/badges/tcs-badge.svg)](tcs_report.md)" >>"${REPORT_FILE}"
for trailer in "${TRAILERS[@]}"; do
  echo "![${trailer} Badge](../static/badges/${trailer}-badge.svg)" >>"${REPORT_FILE}"
done

echo "" >>"${REPORT_FILE}"
echo "## Overview" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"
echo "This report analyzes Git trailer attribution compliance across the ${TOTAL_COMMITS} most recent commits in the repository." >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"
echo "| Metric | Value |" >>"${REPORT_FILE}"
echo "|--------|-------|" >>"${REPORT_FILE}"
echo "| **Overall TCS** | ${TCS}% |" >>"${REPORT_FILE}"
echo "| **Total Commits Analyzed** | ${TOTAL_COMMITS} |" >>"${REPORT_FILE}"
echo "| **Total Trailers Present** | ${TOTAL_PRESENT}/${TOTAL_POSSIBLE} |" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"

echo "## Trailer Compliance" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"
echo "| Trailer | Compliance | Count |" >>"${REPORT_FILE}"
echo "|---------|------------|-------|" >>"${REPORT_FILE}"

for trailer in "${TRAILERS[@]}"; do
  echo "| **${trailer}** | ${trailer_percentages[${trailer}]}% | ${trailer_counts[${trailer}]}/${TOTAL_COMMITS} |" >>"${REPORT_FILE}"
done

echo "" >>"${REPORT_FILE}"
echo "## Missing Trailers" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"
echo "The following commits are missing one or more required trailers:" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"

for trailer in "${TRAILERS[@]}"; do
  if [[ -n "${trailer_missing[${trailer}]}" ]]; then
    echo "### Missing ${trailer}" >>"${REPORT_FILE}"
    echo "" >>"${REPORT_FILE}"
    echo -e "${trailer_missing[${trailer}]}" | while read -r line; do
      if [[ -n "${line}" ]]; then
        echo "${line}" >>"${REPORT_FILE}"
      fi
    done
    echo "" >>"${REPORT_FILE}"
  fi
done

echo "## Recommendations" >>"${REPORT_FILE}"
echo "" >>"${REPORT_FILE}"

if (($(echo "${TCS} >= 90" | bc -l))); then
  echo "✅ **Excellent compliance!** Maintain current practices." >>"${REPORT_FILE}"
elif (($(echo "${TCS} >= 75" | bc -l))); then
  echo "✅ **Good compliance.** Consider addressing missing trailers in future commits." >>"${REPORT_FILE}"
elif (($(echo "${TCS} >= 50" | bc -l))); then
  echo "⚠️ **Moderate compliance.** Use the attribution script consistently: \`./scripts/git-commit-with-trailers.sh\`" >>"${REPORT_FILE}"
else
  echo "❌ **Poor compliance.** Immediate action needed:" >>"${REPORT_FILE}"
  echo "" >>"${REPORT_FILE}"
  echo "1. Always use \`./scripts/git-commit-with-trailers.sh\` for commits" >>"${REPORT_FILE}"
  echo "2. Consider amending recent commits to add missing trailers" >>"${REPORT_FILE}"
  echo "3. Review attribution requirements in README.md" >>"${REPORT_FILE}"
fi

# Clean up
rm "${TMP_COMMITS}"

echo -e "${GREEN}TCS Report generated at ${REPORT_FILE}${NC}"
echo -e "${GREEN}TCS JSON data generated at ${JSON_FILE}${NC}"