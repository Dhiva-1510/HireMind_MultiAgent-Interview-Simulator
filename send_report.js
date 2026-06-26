const nodemailer = require('nodemailer');
const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');

// Read input arguments: json path
const jsonPath = process.argv[2];
if (!jsonPath) {
  console.error("No JSON input path provided.");
  process.exit(1);
}

let data;
try {
  data = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
} catch (err) {
  console.error("Failed to read/parse input JSON:", err);
  process.exit(1);
}

const { email, name, target_role, avg_score, feedback, evaluations } = data;

// Define output path for the PDF
const pdfPath = path.join(path.dirname(jsonPath), `performance_report_${Date.now()}.pdf`);

function generatePDF(pdfPath, callback) {
  const doc = new PDFDocument({ margin: 50 });
  const writeStream = fs.createWriteStream(pdfPath);
  doc.pipe(writeStream);

  // Header branding
  doc.fillColor('#10b981')
     .font('Helvetica-Bold')
     .fontSize(24)
     .text('HireMind AI', { align: 'center' });
  doc.moveDown(0.2);

  doc.fillColor('#6b7280')
     .font('Helvetica')
     .fontSize(10)
     .text('AI-Powered Interview Simulator Performance Report', { align: 'center' });
  doc.moveDown(1.5);

  // Candidate info grid
  doc.fillColor('#111827')
     .font('Helvetica-Bold')
     .fontSize(14)
     .text(`Candidate Performance Report`);
  doc.moveDown(0.5);

  // draw a horizontal line
  doc.strokeColor('#e5e7eb')
     .lineWidth(1)
     .moveTo(50, doc.y)
     .lineTo(550, doc.y)
     .stroke();
  doc.moveDown(0.8);

  doc.fillColor('#374151')
     .font('Helvetica-Bold')
     .fontSize(11)
     .text(`Candidate Name: `, { continued: true })
     .font('Helvetica')
     .text(name || 'N/A');

  doc.font('Helvetica-Bold')
     .text(`Email Address: `, { continued: true })
     .font('Helvetica')
     .text(email);

  doc.font('Helvetica-Bold')
     .text(`Target Role: `, { continued: true })
     .font('Helvetica')
     .text(target_role || 'General Tech Role');

  doc.font('Helvetica-Bold')
     .text(`Average Score: `, { continued: true })
     .font('Helvetica')
     .fillColor('#10b981')
     .text(`${avg_score}/10`);
  doc.moveDown(1);

  // Feedback summary
  doc.fillColor('#111827')
     .font('Helvetica-Bold')
     .fontSize(13)
     .text('Executive Summary & Feedback');
  doc.moveDown(0.5);

  doc.fillColor('#4b5563')
     .font('Helvetica')
     .fontSize(10)
     .text(feedback || 'No summary available.', { align: 'justify', lineGap: 3 });
  doc.moveDown(1.5);

  // Evaluations breakdown
  if (evaluations && evaluations.length > 0) {
    doc.fillColor('#111827')
       .font('Helvetica-Bold')
       .fontSize(13)
       .text('Detailed Performance Breakdown');
    doc.moveDown(0.5);

    evaluations.forEach((val, idx) => {
      // Avoid page-break issues dynamically
      if (doc.y > 650) {
        doc.addPage();
      }

      doc.fillColor('#111827')
         .font('Helvetica-Bold')
         .fontSize(11)
         .text(`Question ${idx + 1}: `, { continued: true })
         .font('Helvetica')
         .text(val.question);
      doc.moveDown(0.3);

      doc.fillColor('#4b5563')
         .font('Helvetica-Bold')
         .text(`Your Answer: `, { continued: true })
         .font('Helvetica')
         .text(val.candidate_answer || '[No Answer]');
      doc.moveDown(0.3);

      doc.fillColor('#10b981')
         .font('Helvetica-Bold')
         .text(`Score: `, { continued: true })
         .text(`${val.overall_score || val.score || 0}/10`);
      doc.moveDown(0.3);

      doc.fillColor('#3b82f6')
         .font('Helvetica-Bold')
         .text(`Evaluator Feedback: `, { continued: true })
         .font('Helvetica')
         .text(val.feedback || 'N/A');
      doc.moveDown(1);
    });
  }

  doc.end();
  writeStream.on('finish', () => {
    callback(null, pdfPath);
  });
  writeStream.on('error', (err) => {
    callback(err);
  });
}

// Mailer Config
const smtpHost = process.env.SMTP_HOST;
const smtpPort = process.env.SMTP_PORT || 587;
const smtpUser = process.env.SMTP_USER;
const smtpPass = process.env.SMTP_PASS;
const smtpFrom = process.env.SMTP_FROM || '"HireMind AI" <reports@hiremind.ai>';

async function sendMail(pdfPath) {
  let transporter;

  if (smtpHost && smtpUser && smtpPass) {
    // Custom SMTP
    transporter = nodemailer.createTransport({
      host: smtpHost,
      port: parseInt(smtpPort),
      secure: parseInt(smtpPort) === 465,
      auth: {
        user: smtpUser,
        pass: smtpPass
      }
    });
  } else {
    // Ethereal Fallback for testing
    console.log("No SMTP settings in environment. Creating test Ethereal account...");
    const testAccount = await nodemailer.createTestAccount();
    transporter = nodemailer.createTransport({
      host: 'smtp.ethereal.email',
      port: 587,
      secure: false,
      auth: {
        user: testAccount.user,
        pass: testAccount.pass
      }
    });
  }

  const mailOptions = {
    from: smtpFrom,
    to: email,
    subject: `Your HireMind AI Performance Report - ${target_role || 'Interview'}`,
    text: `Hello ${name || 'Candidate'},\n\nThank you for practicing with HireMind AI. Please find your detailed interview performance report PDF attached to this email.\n\nAverage Score: ${avg_score}/10\n\nBest regards,\nHireMind AI Team`,
    attachments: [
      {
        filename: `HireMind_Performance_Report.pdf`,
        path: pdfPath
      }
    ]
  };

  const info = await transporter.sendMail(mailOptions);
  console.log("Email sent successfully!");
  console.log("Message ID:", info.messageId);

  // If using Ethereal, log preview link
  if (!smtpHost) {
    const previewUrl = nodemailer.getTestMessageUrl(info);
    console.log("Preview URL:", previewUrl);
    // Write preview URL to a temporary output file so python can read it
    fs.writeFileSync(jsonPath + ".url", previewUrl);
  }

  // Clean up PDF after sending
  try {
    fs.unlinkSync(pdfPath);
  } catch (err) {
    console.error("Failed to delete temp PDF:", err);
  }
}

generatePDF(pdfPath, (err, path) => {
  if (err) {
    console.error("PDF generation failed:", err);
    process.exit(1);
  }
  
  sendMail(path)
    .then(() => {
      // Clean up input json file
      try {
        fs.unlinkSync(jsonPath);
      } catch {}
      process.exit(0);
    })
    .catch((mailErr) => {
      console.error("Email sending failed:", mailErr);
      process.exit(1);
    });
});
