import asyncio
import time
from app.graph.workflow import build_workflow

async def main():
    start_time = time.time()
    app = build_workflow()
    
    # Run the pipeline
    result = await app.ainvoke({
        'youtube_url': 'https://youtu.be/g2cQ2kD6lzs',
        'video_id': '',
        'transcript': [],
        'transcript_chunks': [],
        'candidate_clips': [],
        'validated_clips': [],
        'editing_plans': [],
        'status': 'initialized',
        'errors': [],
        'retry_count': 0,
        'chunk_offset': 0
    })
    
    end_time = time.time()
    
    print('==============================')
    print('PIPELINE COMPLETED')
    print(f"Execution Time: {end_time - start_time:.2f} seconds")
    print(f"Status: {result.get('status')}")
    print(f"Errors: {result.get('errors')}")
    
    validated = result.get('validated_clips', [])
    print(f"Total Validated Clips: {len(validated)}")
    
    for i, clip in enumerate(validated):
        print(f"\n--- Clip {i+1} ---")
        print(f"Title: {clip.get('title')}")
        print(f"Score: {clip.get('match_score')}")
        print(f"Duration: {clip.get('end_time', 0) - clip.get('start_time', 0):.2f}s")
        print(f"Hook: {clip.get('hook_text')}")

        plan = clip.get('editing_plan')
        if plan:
            print("Has Editing Plan: Yes")
            segments = plan.get('segments', [])
            broll_count = sum(1 for s in segments if s.get('visual_type') == 'broll')
            print(f"B-Roll count: {broll_count}")

if __name__ == '__main__':
    asyncio.run(main())
