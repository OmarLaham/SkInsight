document.addEventListener("DOMContentLoaded", function () {

  const quizDataRaw = JSON.parse(document.getElementById("quiz-questions-data").textContent); // quiz-questions-data" is populated in the template using context 
  const quizData = typeof quizDataRaw === 'string' ? JSON.parse(quizDataRaw) : quizDataRaw;

  const questionsContainer = document.getElementById("questionsContainer");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const submitBtn = document.getElementById("submitBtn");
  const progressBar = document.getElementById("progressBar");
  const resultDiv = document.getElementById("result");
  const form = document.getElementById("skinQuiz");

  let currentQuestionIndex = 0;

  // حفظ الإجابات هنا
  const answers = Array(quizData.length).fill(null);

  // عرض السؤال الحالي
  function renderQuestion(index) {
    const question = quizData[index];
    let html = `<fieldset class="space-y-2" aria-live="polite"><legend class="font-medium text-lg mb-2">${index + 1}. ${question.q}</legend>`;
    question.options.forEach((opt, i) => {
      const inputId = `q${index}_opt${i}`;
      const checked = answers[index] === opt.value ? "checked" : "";
      html += `
        <label class="block cursor-pointer select-none">
          <input
            type="radio"
            id="${inputId}"
            name="q${index}"
            value="${opt.value}"
            class="ml-2"
            ${checked}
            required
          />
          ${opt.text}
        </label>
      `;
    });

    html += "</fieldset>";

    questionsContainer.innerHTML = html;

    updateProgressBar();
    updateButtons();
  }

  // تحديث شريط التقدم
  function updateProgressBar() {
    const percent = ((currentQuestionIndex + 1) / quizData.length) * 100;
    progressBar.style.width = percent + "%";
  }

  // تحديث حالة أزرار السابق، التالي والإرسال
  function updateButtons() {
    prevBtn.disabled = currentQuestionIndex === 0;
    nextBtn.disabled = answers[currentQuestionIndex] === null;
    submitBtn.disabled = answers.includes(null);
  }

  // حفظ الإجابة المحددة
  function saveAnswer() {
    const selected = document.querySelector(`input[name="q${currentQuestionIndex}"]:checked`);
    if (selected) {
      answers[currentQuestionIndex] = selected.value;
    } else {
      answers[currentQuestionIndex] = null;
    }
    updateButtons();
  }

  // الاستماع لتغيير الإجابة
  questionsContainer.addEventListener("change", saveAnswer);

  // زر التالي
  nextBtn.addEventListener("click", () => {
    if (currentQuestionIndex < quizData.length - 1) {
      currentQuestionIndex++;
      renderQuestion(currentQuestionIndex);
    }
  });

  // زر السابق
  prevBtn.addEventListener("click", () => {
    if (currentQuestionIndex > 0) {
      currentQuestionIndex--;
      renderQuestion(currentQuestionIndex);
    }
  });

  // عند الإرسال

  form.addEventListener("submit", () => {
    // Remove old hidden inputs if re-submitting
    const oldHiddenInputs = form.querySelectorAll(".answer-hidden-input");
    oldHiddenInputs.forEach(input => input.remove());
  
    // Add new hidden inputs for answers
    answers.forEach((answer, i) => {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = `q${i}`;
      input.value = answer;
      input.classList.add("answer-hidden-input");
      form.appendChild(input);
    });
  
    // No need to call preventDefault() — form will submit as normal

  });
  
  // form.addEventListener("submit", (e) => {
  //   e.preventDefault();
  //   let resultHTML = `<h2 class="text-xl font-semibold mb-2">إجاباتك:</h2><ul class="list-disc list-inside">`;
  //   answers.forEach((answer, i) => {
  //     resultHTML += `<li><strong>س${i + 1}:</strong> ${answer}</li>`;
  //   });
  //   resultHTML += `</ul><p class="mt-4 italic text-gray-700">* هذا ملخص بسيط. يمكن تخصيصه حسب الحاجة.</p>`;

  //   resultDiv.innerHTML = resultHTML;
  //   resultDiv.classList.remove("hidden");
  //   resultDiv.scrollIntoView({ behavior: "smooth" });
  // });

  // العرض الأولي للسؤال الأول
  renderQuestion(currentQuestionIndex);

});
