/**
 * Analyzes text by sending it to the local backend.
 * @param {Object} payload - The payload containing the text to analyze.
 * @param {string} payload.text - The text to analyze.
 * @returns {Promise<Object>} The analysis result.
 */
export async function analyzeText(payload) {
  try {
    const response = await fetch('http://127.0.0.1:8000/predict', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Analysis failed with status ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API Error: ", error);
    throw error;
  }
}
