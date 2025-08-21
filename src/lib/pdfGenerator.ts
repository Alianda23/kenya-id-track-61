import jsPDF from 'jspdf';

interface WaitingCardData {
  applicationNumber: string;
  fullName: string;
  district: string;
  applicationType: string;
  officerName: string;
  date: string;
}

export const generateWaitingCard = (data: WaitingCardData) => {
  const pdf = new jsPDF();
  
  // Set up the document
  pdf.setFontSize(20);
  pdf.setFont('helvetica', 'bold');
  
  // Title
  pdf.text('DIGITAL ID WAITING CARD', 105, 30, { align: 'center' });
  
  // Draw a border
  pdf.rect(20, 50, 170, 180);
  
  // Content
  pdf.setFontSize(12);
  pdf.setFont('helvetica', 'normal');
  
  let yPosition = 70;
  const lineHeight = 20;
  
  // Application Number
  pdf.setFont('helvetica', 'bold');
  pdf.text('Application No:', 30, yPosition);
  pdf.setFont('helvetica', 'normal');
  pdf.text(data.applicationNumber, 100, yPosition);
  
  yPosition += lineHeight;
  
  // Full Name
  pdf.setFont('helvetica', 'bold');
  pdf.text('Full Name:', 30, yPosition);
  pdf.setFont('helvetica', 'normal');
  pdf.text(data.fullName, 100, yPosition);
  
  yPosition += lineHeight;
  
  // District
  pdf.setFont('helvetica', 'bold');
  pdf.text('District:', 30, yPosition);
  pdf.setFont('helvetica', 'normal');
  pdf.text(data.district, 100, yPosition);
  
  yPosition += lineHeight;
  
  // Type of Application
  pdf.setFont('helvetica', 'bold');
  pdf.text('Type of Application:', 30, yPosition);
  pdf.setFont('helvetica', 'normal');
  pdf.text(data.applicationType, 100, yPosition);
  
  yPosition += lineHeight;
  
  // Registration Officer
  pdf.setFont('helvetica', 'bold');
  pdf.text('Registration Officer:', 30, yPosition);
  pdf.setFont('helvetica', 'normal');
  pdf.text(data.officerName, 100, yPosition);
  
  yPosition += lineHeight;
  
  // Date
  pdf.setFont('helvetica', 'bold');
  pdf.text('Date:', 30, yPosition);
  pdf.setFont('helvetica', 'normal');
  pdf.text(data.date, 100, yPosition);
  
  yPosition += lineHeight * 2;
  
  // Signature section
  pdf.setFont('helvetica', 'bold');
  pdf.text('Officer Signature:', 30, yPosition);
  pdf.line(110, yPosition, 170, yPosition); // Signature line
  
  yPosition += lineHeight * 2;
  
  // Important note
  pdf.setFontSize(10);
  pdf.setFont('helvetica', 'italic');
  pdf.text('Note: This acknowledgement is not an identity card', 105, yPosition + 20, { align: 'center' });
  
  // Save the PDF
  const fileName = `application-${data.applicationNumber}.pdf`;
  pdf.save(fileName);
  
  return fileName;
};