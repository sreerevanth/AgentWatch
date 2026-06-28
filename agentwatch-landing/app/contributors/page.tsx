import ContributorsClient from "./ContributorsClient";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Hall of Fame | AgentWatch",
  description: "Meet the elite developers and core operators building AgentWatch.",
};

export const revalidate = 3600; // Revalidate every hour

async function getContributors() {
  try {
    const headers = { Accept: "application/vnd.github.v3+json" };
    
    // 1. Fetch contributors (for commits & avatars)
    const contRes = await fetch("https://api.github.com/repos/sreerevanth/agentwatch/contributors?per_page=100", { 
      headers, 
      next: { revalidate: 3600 } 
    });
    const contributorsData = contRes.ok ? await contRes.json() : [];

    // 2. Fetch all PRs to get accurate PR counts per user
    // (We fetch up to 300 PRs which covers the current repo size of ~200)
    const prRequests = [1, 2, 3].map(p => 
      fetch(`https://api.github.com/repos/sreerevanth/agentwatch/pulls?state=all&per_page=100&page=${p}`, { 
        headers, 
        next: { revalidate: 3600 } 
      })
      .then(res => res.ok ? res.json() : [])
    );
    const prResults = await Promise.all(prRequests);
    const allPRs = prResults.flat();

    const prCounts: Record<string, number> = {};
    allPRs.forEach((pr: any) => {
      // Only count PRs that have been merged
      if (pr.user && pr.user.login && pr.merged_at) {
        prCounts[pr.user.login] = (prCounts[pr.user.login] || 0) + 1;
      }
    });

    // 3. Combine the data
    const userMap = new Map();

    // Add everyone from contributors list
    contributorsData.forEach((c: any) => {
      userMap.set(c.login, {
        username: c.login,
        avatarUrl: c.avatar_url,
        commits: c.contributions || 0,
        prs: prCounts[c.login] || 0
      });
    });

    // Add anyone who has PRs but wasn't in the contributors list yet
    allPRs.forEach((pr: any) => {
      if (pr.user && pr.user.login && !userMap.has(pr.user.login)) {
        userMap.set(pr.user.login, {
          username: pr.user.login,
          avatarUrl: pr.user.avatar_url,
          commits: 0,
          prs: prCounts[pr.user.login] || 0
        });
      }
    });

    // 4. Ensure SHAURYASANYAL3 is in the list so their name can be displayed,
    // but use their REAL PR count (0 if they haven't made PRs to the main repo yet)
    // so the leaderboard remains authentic.
    if (!userMap.has("SHAURYASANYAL3")) {
      userMap.set("SHAURYASANYAL3", {
        username: "SHAURYASANYAL3",
        avatarUrl: "https://avatars.githubusercontent.com/u/128920982?v=4",
        commits: 0,
        prs: 0
      });
    }

    // 5. Format for the UI
    let finalContributors = Array.from(userMap.values()).map((c: any) => {
      let role = c.prs >= 5 ? "Core Contributor" : "Contributor";
      let specialContribution = `Actively contributed with ${c.prs} merged PR${c.prs !== 1 ? 's' : ''}.`;
      
      if (c.username === "sreerevanth") {
        role = "Creator of AgentWatch";
        specialContribution = "Creator and lead maintainer of the AgentWatch core engine.";
      } else if (c.username === "SHAURYASANYAL3") {
        role = c.prs >= 5 ? "Core Contributor - Frontend Creator" : "Contributor - Frontend Creator";
        specialContribution = `Architected the frontend. Contributed ${c.prs} merged PR${c.prs !== 1 ? 's' : ''} to the repository.`;
      }

      return {
        username: c.username,
        avatarUrl: c.avatarUrl,
        role,
        stats: { prs: c.prs, commits: c.commits },
        specialContribution
      };
    });

    // 6. Sort strictly by PRs descending (real leaderboard)
    finalContributors.sort((a, b) => b.stats.prs - a.stats.prs);

    // Filter out users with 0 PRs from the top section to keep the leaderboard clean, 
    // unless it's the frontend creator or backend creator to ensure they appear somewhere.
    finalContributors = finalContributors.filter(c => 
      c.stats.prs > 0 || c.username === "SHAURYASANYAL3" || c.username === "sreerevanth"
    );

    return finalContributors;
  } catch (error) {
    console.error("Error fetching contributors:", error);
    // Fallback data
    return [
      {
        username: "sreerevanth",
        avatarUrl: "https://avatars.githubusercontent.com/u/86904394?v=4",
        role: "Creator of AgentWatch",
        stats: { prs: 10, commits: 39 },
        specialContribution: "Creator and lead maintainer of the AgentWatch core engine."
      },
      {
        username: "SHAURYASANYAL3",
        avatarUrl: "https://avatars.githubusercontent.com/u/128920982?v=4",
        role: "Contributor - Frontend Creator",
        stats: { prs: 0, commits: 0 },
        specialContribution: "Architected the frontend."
      }
    ];
  }
}

export default async function ContributorsPage() {
  const contributors = await getContributors();

  return <ContributorsClient contributors={contributors} />;
}
