# LikedLens – AI-Powered Instagram Liked Reels & Posts Finder

### Project Description

Instagram allows users to view their previously liked Reels and posts through the Your Activity section. However, finding a specific Reel or post from hundreds or thousands of liked items can be difficult because Instagram does not provide an advanced search feature to filter liked content based on specific keywords, hashtags, or the actual content within a Reel or post.

LikedLens is designed to solve this problem by providing an intelligent search and filtering system for previously liked Instagram content.

The application allows users to search their liked Reels and posts using specific keywords or hashtags. Unlike traditional caption-based searches, LikedLens also incorporates AI-powered content analysis to identify relevant content based on what actually appears in an image or video, or what is spoken in a Reel, even when the search keyword is not mentioned in the caption.

### Why This Project?

Imagine liking a Reel about a chicken biryani recipe a few months ago. Later, you want to watch that Reel again, but you have liked hundreds of other Reels since then.

Instagram lets you browse your liked Reels, but finding that particular recipe may require scrolling through your entire liked history.

With LikedLens, you can simply search for "Chicken Biryani", and the application can identify relevant liked Reels by analyzing their captions, hashtags, video frames, or spoken content, provided that the necessary media data is available.

### Key Features

1. Keyword and Hashtag Search: Filter previously liked Reels and posts based on words or hashtags in their available captions and descriptions.
2. AI-Powered Content Search: Analyze images and videos to identify content relevant to search keywords, even if the keywords are not explicitly mentioned in the captions.
3. Audio Analysis: Transcribe speech from available Reel audio to help identify relevant content.
4. Content Type Filtering: Search specifically within Reels, posts, or both.
5. Multiple Keyword Search: Search for multiple topics simultaneously.
6. Organized Search Results: Display matching content with available thumbnails, captions, and direct links to the original Instagram posts.
7. Privacy-Focused Approach: Use Instagram-exported activity data rather than requesting users' Instagram passwords.

### How Is This Different from Instagram?

| Instagram's Existing Feature | LikedLens |
|---|---|
| View previously liked posts and Reels | Search within previously liked content |
| Browse liked content manually | Filter by keywords and hashtags |
| Limited filtering options | Filter by content type and multiple keywords |
| No AI-based semantic search of liked media | Analyze images, videos, and spoken audio |
| Finding older liked content may take time | Surface relevant content more efficiently |

### Technologies Used

- Python: Core application logic and data processing.
- Streamlit: Interactive web interface.
- CLIP AI Model: Image and video-frame content understanding.
- Whisper: Audio transcription and speech recognition.
- Pandas: Data processing and search result management.

### Technical Limitation

Instagram's official API does not currently provide access to a user's complete liked-content history. Therefore, LikedLens uses Instagram activity exports to identify liked content. Advanced image, video, and audio analysis works when the corresponding media files are available to the application.

### Project Objective

The main objective of LikedLens is to transform Instagram's liked-content history from a collection that users manually browse into an intelligent, searchable personal content library.

Instead of remembering when a Reel was liked or scrolling through hundreds of posts, users can search for what they remember about the content and quickly find relevant results.