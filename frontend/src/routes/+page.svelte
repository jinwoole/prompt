<script lang="ts">
  // 완전히 새로운 미니멀한 페이지
</script>

<div class="max-w-4xl mx-auto px-10 py-20">
  <!-- 메인 타이틀 -->
  <div class="text-center mb-16">
    <h1 class="text-[40px] font-semibold text-black tracking-[-0.032em] mb-4">
      AI 프롬프트 작성
    </h1>
    <p class="text-[17px] text-gray-600 tracking-[-0.022em]">
      명확하고 효과적인 프롬프트를 작성하세요.
    </p>
  </div>
  
  <!-- 메인 에디터 영역 -->
  <div class="bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
    <textarea
      placeholder="프롬프트를 입력하세요..."
      class="w-full h-64 resize-none text-[16px] text-black tracking-[-0.022em] leading-relaxed placeholder-gray-400"
    ></textarea>
    
    <!-- 하단 액션 바 -->
    <div class="flex justify-between items-center mt-6 pt-6 border-t border-gray-200">
      <div class="text-[14px] text-gray-500">
        0 글자
      </div>
      
      <div class="flex items-center space-x-3">
        <button class="px-4 py-2 text-[14px] text-gray-600 hover:text-black transition-colors">
          지우기
        </button>
        <button class="px-6 py-2 bg-black text-white text-[14px] font-medium rounded-lg hover:bg-gray-800 transition-colors">
          복사
        </button>
      </div>
    </div>
  </div>
</div>
