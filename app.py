import os
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from textblob import TextBlob
import networkx as nx
import matplotlib.pyplot as plt
from langdetect import detect, LangDetectException
import re
import textwrap
import urllib.parse


# Set up the YouTube Data API client
DEVELOPER_KEY = 'AIzaSyDYi0hx3ReDAlCz3GXom7hyj8t0vvjWcKs'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

def extract_video_id(url):
    query = urllib.parse.urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = urllib.parse.parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    raise ValueError('Invalid YouTube URL or unable to extract video ID.')



def get_comments(video_id):
    try:
        # Retrieve the comments for the specified video
        response = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            textFormat='plainText',
            maxResults=100,  # Adjust this value to retrieve more comments if needed
        ).execute()

        comments = []
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)

        return comments
    except HttpError as e:
        print(f'An error occurred: {e}')
        return []


def save_comments(hashtag, comments):
    positive_comments = []
    negative_comments = []
    question_comments = []
    neutral_comments = []

    positive_words = ["good", "great", "excellent", "nice", "super", "fabulous", "smooth", "best", "love", "fantastic",
                      "wow", "amazing","promising"]
    negative_words = ["bad", "poor", "terrible", "worst", "damage", "flop", "waste", "waste of money", "dont buy",
                      "horrible", "failure", "bullshit", "hell", "not available","repair" "avoid", "cheap","issue","never","error","scam"]
    question_words = ["how", "where", "what", "when", "?", "who"]

    unique_comments = set()  # Store unique comments to remove duplicates

    for comment in comments:
        try:
            # Remove special characters from the comment using regular expressions
            comment = re.sub(r'[^\w\s]', '', comment)

            # Detect the language of the comment
            language = detect(comment)

            # Filter comments that are not in English
            if language != 'en':
                continue

            # Perform sentiment analysis
            blob = TextBlob(comment)
            polarity = blob.sentiment.polarity

            if polarity > 0 and any(word in comment.lower() for word in positive_words):
                positive_comments.append((comment, polarity))
            elif polarity < 0 and any(word in comment.lower() for word in negative_words):
                negative_comments.append((comment, polarity))
            elif any(word.lower() in comment.lower() for word in question_words):
                question_comments.append((comment, polarity))
            else:
                neutral_comments.append((comment, polarity))

            # Add comment to unique comments set
            unique_comments.add(comment)

        except LangDetectException:
            continue

    # Convert unique comments set back to a list
    unique_comments = list(unique_comments)

    # Sort the comments based on polarity
    positive_comments.sort(key=lambda x: x[1], reverse=True)
    negative_comments.sort(key=lambda x: x[1])
    neutral_comments.sort(key=lambda x: x[1])
    question_comments.sort(key=lambda x: x[1])

    filename_positive = f'{hashtag}_positive_comments.txt'
    filename_negative = f'{hashtag}_negative_comments.txt'
    filename_question = f'{hashtag}_question_comments.txt'
    filename_neutral = f'{hashtag}_neutral_comments.txt'

    with open(filename_positive, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in positive_comments]))

    with open(filename_negative, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in negative_comments]))

    with open(filename_question, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in question_comments]))

    with open(filename_neutral, 'w', encoding='utf-8') as file:
        file.write('\n'.join([f'{comment[0]} (Polarity: {comment[1]})' for comment in neutral_comments]))

    print(f'Successfully saved {len(positive_comments)} positive comments to {filename_positive}.')
    print(f'Successfully saved {len(negative_comments)} negative comments to {filename_negative}.')
    print(f'Successfully saved {len(question_comments)} question comments to {filename_question}.')
    print(f'Successfully saved {len(neutral_comments)} neutral comments to {filename_neutral}.')

    create_knowledge_graph(hashtag, len(positive_comments), len(negative_comments), len(neutral_comments),
                           len(question_comments), len(unique_comments), unique_comments)  # Pass total_comments_count

question_words = ["how", "where", "what", "when", "?", "who"]
def create_knowledge_graph(hashtag, positive_count, negative_count, neutral_count, question_count,
                           total_comments_count,
                           comments):
    # Remove special characters from comments using regular expressions
    comments = [re.sub(r'[^\w\s]', '', comment) for comment in comments]

    # Create a graph
    graph = nx.DiGraph()

    # Add the sentiment nodes with count information
    graph.add_node('Positive', count=positive_count)
    graph.add_node('Negative', count=negative_count)
    graph.add_node('Neutral', count=neutral_count)
    graph.add_node('Questions', count=question_count)
    if 2:
        graph.add_node('Total Comments', count=total_comments_count)
        # Add edge from the parent node to the total comments node
        graph.add_edge(hashtag, 'Total Comments', weight=total_comments_count)
    else:
        #graph.add_node(hashtag, count=total_comments_count)  # Add the parent node with total comments count
        # Add edges from the parent node to sentiment nodes
        graph.add_edge(hashtag, 'Positive', weight=positive_count)
        graph.add_edge(hashtag, 'Negative', weight=negative_count)
        graph.add_edge(hashtag, 'Neutral', weight=neutral_count)
        graph.add_edge(hashtag, 'Questions', weight=question_count)

    graph.add_node(hashtag, count=total_comments_count)  # Add the parent node with total comments count

    # Add edges from the parent node to sentiment nodes
    graph.add_edge(hashtag, 'Positive', weight=positive_count)
    graph.add_edge(hashtag, 'Negative', weight=negative_count)
    graph.add_edge(hashtag, 'Neutral', weight=neutral_count)
    graph.add_edge(hashtag, 'Questions', weight=question_count)

    # Add subnodes to sentiment nodes
    sentiment_nodes = ['Positive', 'Negative', 'Neutral', 'Questions']
    subnode_colors = ['palegreen', 'lightcoral', 'lightblue', 'lightyellow']

    for i, sentiment in enumerate(sentiment_nodes):
        sentiment_comments = set()  # Store comments for each sentiment to remove duplicates

        if sentiment == 'Positive':
            sentiment_comments = {comment for comment in comments if TextBlob(comment).sentiment.polarity > 0}
        elif sentiment == 'Negative':
            sentiment_comments = {comment for comment in comments if TextBlob(comment).sentiment.polarity < 0}
        elif sentiment == 'Neutral':
            sentiment_comments = {comment for comment in comments if TextBlob(comment).sentiment.polarity == 0}
        elif sentiment == 'Questions':
            sentiment_comments = {comment for comment in comments if
                                   any(word.lower() in comment.lower() for word in question_words)}

        subnode_comments = list(sentiment_comments)[:3]  # Get the first three comments for each sentiment

        for j, comment in enumerate(subnode_comments):
            subnode_label = f'{sentiment}_sub{j}'
            truncated_comment = textwrap.shorten(comment, width=95, placeholder='...')
            graph.add_node(subnode_label, label=truncated_comment)
            graph.add_edge(sentiment, subnode_label, weight=1)

    # Draw the graph
    pos = nx.spring_layout(graph, k=1.3)  # Adjust 'k' value to control the node spacing
    node_colors = ['lightgreen', 'lightcoral', 'lightskyblue', 'lightyellow', 'lightgray']  # Add a color for the parent node

    # Draw the sentiment nodes and subnodes
    for i, node in enumerate(sentiment_nodes):
        nx.draw_networkx_nodes(graph, pos, nodelist=[node], node_color=node_colors[i], node_size=1500, alpha=0.8)

        # Draw the subnodes
        subnodes = [n for n in graph.nodes if node in n and 'sub' in n]
        nx.draw_networkx_nodes(graph, pos, nodelist=subnodes, node_color=subnode_colors[i], node_size=1000, alpha=0.8)

    # Draw the parent node
    nx.draw_networkx_nodes(graph, pos, nodelist=[hashtag], node_color=node_colors[-1], node_size=1500, alpha=0.8)

    # Draw the edges
    nx.draw_networkx_edges(graph, pos, width=1.0, alpha=0.5, arrowsize=10)

    # Add labels to nodes
    labels = {node: graph.nodes[node].get('label', f"{node} ({graph.nodes[node].get('count', 0)})") for node in
              graph.nodes}
    nx.draw_networkx_labels(graph, pos, labels=labels, font_size=8, font_weight='bold')

    # Set the plot title
    plt.title(f'Knowledge Graph for Hashtag: {hashtag}')

    # Save the plot as a PNG image
    filename = f'{hashtag}_knowledge_graph.png'
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(filename)
    print(f'Successfully saved the knowledge graph as {filename}.')
    plt.show()
    
     
def main():
    # Get the user input
    option = input("Choose an option:\n1. Search for videos based on a hashtag\n2. Extract comments from a video link\n")
    if option == '1':
        # Get the hashtag input from the user
        hashtag = input('Enter a hashtag: ')

        try:
            # Search for videos based on the hashtag
            response = youtube.search().list(
                part='id',
                q=hashtag,
                type='video',
                maxResults=10,  # Adjust this value to retrieve more videos if needed
            ).execute()

            video_ids = [item['id']['videoId'] for item in response['items']]
            all_comments = []
            for video_id in video_ids:
                comments = get_comments(video_id)
                all_comments.extend(comments)

            save_comments(hashtag, all_comments)
        except HttpError as e:
            print(f'An error occurred: {e}')
    elif option == '2':
        # Get the video link input from the user
        video_link = input('Enter a video link: ')
        video_id = extract_video_id(video_link)
        if video_id:
            comments = get_comments(video_id)
            save_comments(video_id, comments)
        else:
            print('Invalid video link.')
    else:
        print('Invalid option. Please choose either 1 or 2.')


if __name__ == '__main__':
    main()
